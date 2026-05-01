"""Session — one running debate. Owns the FSM, the event stream, the swap
queue, and (eventually) the verdict.

This is what `Pantheon.debate(...)` returns. Used either as a regular
async-context value (call `await session.run()`) or via streaming
(`async for event in session.stream()`), with an optional terminal
`await session.verdict()`.
"""
from __future__ import annotations

import asyncio
import secrets
import time
import uuid
from dataclasses import dataclass, field

from pantheon.core.agent import Agent
from pantheon.core.persona import Persona
from pantheon.core.relay import compose_handoff
from pantheon.core.weights import compute_weights
from pantheon.debate.fsm import Phase, is_legal
from pantheon.debate.phases import (
    CrossExamPhase,
    OpeningPhase,
    PhaseContext,
    RebuttalPhase,
    SynthesisPhase,
)
from pantheon.obs.budget import BudgetExceeded, BudgetGuard
from pantheon.obs.otel import maybe_span, no_op_trace_id
from pantheon.obs.replay import Recorder, debate_id_for
from pantheon.roles.auditor import Auditor
from pantheon.roles.moderator import Moderator
from pantheon.roles.oracle import Oracle
from pantheon.types.events import (
    DebateEvent,
    PhaseBoundaryEvent,
    SpeechEvent,
    SwapEvent,
    SystemEvent,
    VerdictEvent,
)
from pantheon.types.verdict import CostBreakdown, RelayLogEntry, Verdict


@dataclass
class _PendingSwap:
    seat: int
    kind: str  # "persona" | "model" | "memory"
    target: object  # Persona | Model | EpisodicStore


@dataclass
class Session:
    session_id: str
    debate_id: str
    question: str
    agents: list[Agent]
    moderator: Moderator
    oracle: Oracle
    auditor: Auditor
    budget: BudgetGuard
    recorder: Recorder | None
    topic_tags: dict[str, float] = field(default_factory=dict)
    user_weights: dict[int, float] = field(default_factory=dict)
    rounds: int = 3
    seed: int | None = None

    _phase: Phase = Phase.CREATED
    _pending_swaps: list[_PendingSwap] = field(default_factory=list)
    _swap_warnings: list[str] = field(default_factory=list)
    _relay_log: list[RelayLogEntry] = field(default_factory=list)
    _events: asyncio.Queue[DebateEvent | None] = field(default_factory=asyncio.Queue)
    _seq: int = 0
    _verdict: Verdict | None = None
    _trace_id: str = ""
    _cost: CostBreakdown = field(default_factory=CostBreakdown)
    _model_calls: int = 0
    _started_at: float = 0.0
    _devil_advocate_invoked: bool = False
    _consumed: bool = False

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = uuid.uuid4().hex
        if not self.debate_id:
            self.debate_id = secrets.token_hex(8)
        self._trace_id = no_op_trace_id()

    # ---------- swap queue API ----------

    def queue_swap_persona(
        self, seat: int, to_persona: Persona, *, instance_suffix: str = ""
    ) -> None:
        self._pending_swaps.append(
            _PendingSwap(seat=seat, kind="persona", target=(to_persona, instance_suffix))
        )

    def queue_swap_model(self, seat: int, to_model) -> None:
        self._pending_swaps.append(_PendingSwap(seat=seat, kind="model", target=to_model))

    # ---------- streaming API ----------

    async def stream(self):
        """Yield events as the debate runs. Call once."""
        if self._consumed:
            raise RuntimeError("Session already consumed; replay via debate_id.")
        self._consumed = True
        runner = asyncio.create_task(self._run())
        try:
            while True:
                ev = await self._events.get()
                if ev is None:
                    break
                yield ev
        finally:
            await runner  # propagate any exception

    async def run(self) -> Verdict:
        """Run the debate to completion and return the verdict.
        Drains the event stream internally."""
        async for _ in self.stream():
            pass
        assert self._verdict is not None
        return self._verdict

    async def verdict(self) -> Verdict:
        if self._verdict is None:
            return await self.run()
        return self._verdict

    # ---------- internal ----------

    async def _emit(self, ev: DebateEvent) -> None:
        # Override seq with the session's monotonic counter so all events have
        # globally unique ordered seq numbers regardless of which subsystem
        # produced them.
        ev = ev.model_copy(update={"seq": self._next_seq()})
        await self._events.put(ev)
        if self.recorder is not None:
            self.recorder.write("debate_event", **ev.model_dump())

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def _transition(self, dst: Phase) -> None:
        if not is_legal(self._phase, dst):
            raise RuntimeError(f"illegal transition {self._phase} → {dst}")
        ev = PhaseBoundaryEvent(
            session_id=self.session_id,
            seq=self._next_seq(),
            from_phase=self._phase.value,
            to_phase=dst.value,
        )
        await self._emit(ev)
        await self._apply_pending_swaps(at_phase=dst.value)
        self._phase = dst

    async def _apply_pending_swaps(self, *, at_phase: str) -> None:
        if not self._pending_swaps:
            return
        for swap in self._pending_swaps:
            ag = next((a for a in self.agents if a.seat == swap.seat), None)
            if ag is None:
                continue
            if swap.kind == "persona":
                new_persona, suffix = swap.target  # type: ignore[misc]
                from_label = ag.label
                from_display = ag.persona.display_name
                ag.swap_persona(new_persona, instance_suffix=suffix)
                self._relay_log.append(
                    RelayLogEntry(
                        seat=ag.seat,
                        from_persona=from_label,
                        to_persona=ag.label,
                        at_phase=at_phase,
                    )
                )
                handoff = compose_handoff(from_display, ag.persona.display_name)
                # Stash handoff onto agent; Agent.speak will consume it on the
                # next call.
                ag.pending_handoff = handoff
                await self._emit(
                    SwapEvent(
                        session_id=self.session_id,
                        seq=0,  # set in _emit
                        seat=ag.seat,
                        kind="persona",
                        from_id=from_label,
                        to_id=ag.label,
                        handoff_statement=handoff,
                    )
                )
            elif swap.kind == "model":
                from_id = ag.model.id
                ag.swap_model(swap.target)  # type: ignore[arg-type]
                await self._emit(
                    SwapEvent(
                        session_id=self.session_id,
                        seq=0,  # set in _emit
                        seat=ag.seat,
                        kind="model",
                        from_id=from_id,
                        to_id=ag.model.id,
                    )
                )
            else:  # memory
                ag.swap_memory(swap.target)  # type: ignore[arg-type]
                await self._emit(
                    SwapEvent(
                        session_id=self.session_id,
                        seq=0,  # set in _emit
                        seat=ag.seat,
                        kind="memory",
                        from_id="<prev>",
                        to_id="<new>",
                    )
                )

            # Track swap warnings.
            persona_swaps_this_seat = sum(
                1 for s in ag.swap_log if s[0] == "persona"
            )
            if persona_swaps_this_seat > 5:
                msg = f"seat {ag.seat} unstable: {persona_swaps_this_seat} persona swaps"
                if msg not in self._swap_warnings:
                    self._swap_warnings.append(msg)

        self._pending_swaps.clear()

    async def _run_phase_strategy(
        self, strategy, ctx: PhaseContext, phase_name: str
    ) -> None:
        """Run a phase strategy. Wraps each agent.speak with budget check,
        OTel span, and cost accounting. Handoff prefixes are consumed
        automatically by Agent.speak via `pending_handoff`."""
        original_speak: dict[int, callable] = {}
        for ag in self.agents:
            original_speak[ag.seat] = ag.speak

            async def _wrapped(prompt, *, phase, _ag=ag, _orig=ag.speak, **kw):
                self.budget.check()
                with maybe_span(
                    "llm.call",
                    seat=_ag.seat,
                    persona=_ag.persona.id,
                    model=_ag.model.id,
                    phase=phase,
                ):
                    res = await _orig(prompt, phase=phase, **kw)
                self._account(res, _ag)
                return res

            ag.speak = _wrapped  # type: ignore[method-assign]

        try:
            async for event in strategy.run(self.agents, ctx):
                # Audit each claim before emitting.
                claim = ctx.claims[-1] if ctx.claims else None
                if claim is not None:
                    persona = next(
                        (a.persona for a in self.agents if a.persona.id == event.persona_id),
                        None,
                    )
                    await self.auditor.audit_claim(claim, persona)
                event.phase = phase_name  # type: ignore[misc]
                await self._emit(event)
        finally:
            for ag in self.agents:
                if ag.seat in original_speak:
                    ag.speak = original_speak[ag.seat]  # type: ignore[method-assign]

    def _account(self, result, agent: Agent) -> None:
        self._cost.total_usd += result.cost_usd
        self._cost.total_calls += 1
        self._cost.by_seat[agent.seat] = (
            self._cost.by_seat.get(agent.seat, 0.0) + result.cost_usd
        )
        self._cost.by_model[agent.model.id] = (
            self._cost.by_model.get(agent.model.id, 0.0) + result.cost_usd
        )
        self._model_calls += 1
        self.budget.record(result.cost_usd)
        if self.recorder is not None:
            # The Agent.speak path doesn't expose the raw messages list, so we
            # log a thin call record here. Full LLM message logging happens
            # at the gateway level (M1 will expose a hook).
            self.recorder.write(
                "llm_call_summary",
                seat=agent.seat,
                persona=agent.persona.id,
                model=agent.model.id,
                cost_usd=result.cost_usd,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
            )

    async def _run(self) -> None:
        self._started_at = time.monotonic()
        ctx = PhaseContext(
            session_id=self.session_id,
            question=self.question,
            rounds_remaining=self.rounds,
        )
        try:
            await self._transition(Phase.OPENING)
            await self._run_phase_strategy(OpeningPhase(), ctx, "opening")

            await self._transition(Phase.CROSS_EXAM)
            await self._run_phase_strategy(CrossExamPhase(), ctx, "cross_exam")

            await self._transition(Phase.REBUTTAL)
            await self._run_phase_strategy(RebuttalPhase(), ctx, "rebuttal")

            # Synthesis loop
            soft = self.moderator.soft_consensus(ctx)
            for r in range(max(0, self.rounds - 2)):
                ctx.rounds_remaining = self.rounds - 2 - r
                await self._transition(Phase.SYNTHESIS)
                summary = await self.moderator.summarize(ctx)
                await self._emit(
                    SystemEvent(
                        session_id=self.session_id,
                        seq=0,  # set in _emit
                        role="moderator",
                        message=summary,
                    )
                )
                if self.moderator.soft_consensus(ctx):
                    soft = True
                    self._devil_advocate_invoked = True  # M1 will actually summon one
                    await self._emit(
                        SystemEvent(
                            session_id=self.session_id,
                            seq=0,  # set in _emit
                            role="moderator",
                            message=(
                                "Soft consensus detected; in M1 a devil's advocate "
                                "would be summoned here."
                            ),
                        )
                    )
                await self._run_phase_strategy(SynthesisPhase(summary), ctx, "synthesis")

            await self._transition(Phase.VERDICT)
            weights = compute_weights(
                self.agents, self.topic_tags, user_prefs=self.user_weights
            )
            duration_ms = int((time.monotonic() - self._started_at) * 1000)
            self._verdict = await self.oracle.render_verdict(
                session_id=self.session_id,
                debate_id=self.debate_id,
                question=self.question,
                agents=self.agents,
                weights=weights,
                ctx=ctx,
                topic_tags=self.topic_tags,
                relay_log=self._relay_log,
                swap_warnings=self._swap_warnings,
                trace_id=self._trace_id,
                cost=self._cost,
                duration_ms=duration_ms,
                model_calls=self._model_calls,
                soft_consensus=soft,
                devil_advocate_invoked=self._devil_advocate_invoked,
            )
            await self._emit(
                VerdictEvent(
                    session_id=self.session_id,
                    seq=0,  # set in _emit
                    debate_id=self.debate_id,
                )
            )
            if self.recorder is not None:
                self.recorder.write("verdict", verdict=self._verdict)
            await self._transition(Phase.CLOSED)
        except BudgetExceeded as e:
            await self._degrade(f"budget exceeded: {e}")
        except Exception as e:  # noqa: BLE001 — top-level supervisor
            await self._degrade(f"unhandled error: {e!r}")
            raise
        finally:
            await self._events.put(None)
            if self.recorder is not None:
                self.recorder.close()

    async def _degrade(self, reason: str) -> None:
        await self._emit(
            SystemEvent(
                session_id=self.session_id,
                seq=0,  # set in _emit
                role="framework",
                message=f"DEGRADED: {reason}",
            )
        )
        if is_legal(self._phase, Phase.DEGRADED):
            self._phase = Phase.DEGRADED
        # No verdict produced; caller can resume() in a future iteration (M1).


def make_debate_id(question: str, agents: list[Agent], seed: int | None) -> str:
    sig = "|".join(f"{a.seat}:{a.persona.id}:{a.model.id}" for a in agents)
    return debate_id_for(question, sig, seed)
