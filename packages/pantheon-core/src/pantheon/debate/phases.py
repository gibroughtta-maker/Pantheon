"""Phase strategies — each phase = `prepare → execute → reduce`.

A `PhaseStrategy` runs all participating agents through the phase. Speech
events are yielded as an async iterator so the Session can stream them.
The strategy never mutates Pantheon's swap queue directly; that's the
coordinator's job at phase boundaries.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol

from pantheon.core.agent import Agent
from pantheon.types.events import SpeechEvent
from pantheon.types.verdict import Claim


@dataclass
class PhaseContext:
    """Mutable per-debate context handed to each phase."""

    session_id: str
    question: str
    rounds_remaining: int
    seq_counter: int = 0  # event sequence
    transcripts: dict[int, list[str]] = field(default_factory=dict)  # seat → texts
    claims: list[Claim] = field(default_factory=list)

    def next_seq(self) -> int:
        self.seq_counter += 1
        return self.seq_counter


class PhaseStrategy(Protocol):
    name: str

    async def run(
        self,
        agents: list[Agent],
        ctx: PhaseContext,
    ) -> AsyncIterator[SpeechEvent]: ...


def _record_speech(ctx: PhaseContext, agent: Agent, text: str) -> SpeechEvent:
    ctx.transcripts.setdefault(agent.seat, []).append(text)
    ctx.claims.append(
        Claim(
            claim_id=f"c{len(ctx.claims) + 1}",
            speaker=agent.label,
            text=text[:500],
        )
    )
    return SpeechEvent(
        session_id=ctx.session_id,
        seq=ctx.next_seq(),
        seat=agent.seat,
        persona_id=agent.persona.id,
        phase="(set by caller)",
        text=text,
        model_id=agent.model.id,
    )


async def _gather_speeches(
    agents: list[Agent],
    ctx: PhaseContext,
    prompt_for: callable,
    phase_name: str,
    *,
    prefixes: dict[int, str] | None = None,
) -> list[SpeechEvent]:
    """Run all agents in parallel. Each agent's speech is appended to its
    own working memory. Order of yielded events is by seat for determinism."""
    prefixes = prefixes or {}

    async def _one(ag: Agent) -> SpeechEvent:
        prompt = prompt_for(ag)
        result = await ag.speak(prompt, phase=phase_name, prefix=prefixes.get(ag.seat, ""))
        ev = _record_speech(ctx, ag, result.text)
        ev.phase = phase_name  # type: ignore[misc]
        return ev

    results = await asyncio.gather(*[_one(a) for a in agents])
    return sorted(results, key=lambda e: e.seat)


class OpeningPhase:
    name = "opening"

    async def run(self, agents, ctx):
        def prompt_for(_ag):
            return (
                f"OPENING STATEMENT.\n"
                f"The question before this Pantheon is: {ctx.question!r}\n\n"
                "Give your initial position and your two strongest reasons. "
                "Do not refer to other speakers yet — they have not spoken. "
                "If you must quote yourself or your tradition, be specific about "
                "which work and where."
            )

        events = await _gather_speeches(agents, ctx, prompt_for, self.name)
        for e in events:
            yield e


class CrossExamPhase:
    name = "cross_exam"

    async def run(self, agents, ctx):
        # Build a digest of all openings the persona will see.
        digest_lines = []
        for seat in sorted(ctx.transcripts):
            persona_id = next(a.persona.id for a in agents if a.seat == seat)
            text = ctx.transcripts[seat][-1]
            digest_lines.append(f"[seat {seat} | {persona_id}] {text}")
        digest = "\n\n".join(digest_lines)

        def prompt_for(_ag):
            return (
                f"CROSS-EXAMINATION.\n\nThe other speakers said:\n\n{digest}\n\n"
                "Pick the speaker whose view is most opposite to your own and "
                "ask them ONE specific, probing question. Do not give a speech; "
                "the question must be answerable. Address them by name."
            )

        events = await _gather_speeches(agents, ctx, prompt_for, self.name)
        for e in events:
            yield e


class RebuttalPhase:
    name = "rebuttal"

    async def run(self, agents, ctx):
        digest_lines = []
        for seat in sorted(ctx.transcripts):
            persona_id = next(a.persona.id for a in agents if a.seat == seat)
            text = ctx.transcripts[seat][-1]
            digest_lines.append(f"[seat {seat} | {persona_id}] {text}")
        digest = "\n\n".join(digest_lines)

        def prompt_for(_ag):
            return (
                f"REBUTTAL.\nOthers' last words:\n\n{digest}\n\n"
                "Address the questions and counter-arguments aimed at you. "
                "If a critique lands, say so explicitly and revise your position. "
                "If it misses, explain why in one paragraph."
            )

        events = await _gather_speeches(agents, ctx, prompt_for, self.name)
        for e in events:
            yield e


class SynthesisPhase:
    """One pass of moderator-driven synthesis. Multiple iterations are
    orchestrated by the Session, not within this strategy."""

    name = "synthesis"

    def __init__(self, moderator_summary: str = "") -> None:
        self.moderator_summary = moderator_summary

    async def run(self, agents, ctx):
        def prompt_for(_ag):
            return (
                f"SYNTHESIS — round {ctx.rounds_remaining}.\n\n"
                f"The moderator has summarized the debate so far:\n\n"
                f"{self.moderator_summary or '(no summary yet)'}\n\n"
                "Where do you now stand? Identify ONE point you concede to "
                "others, and ONE point you still hold against them. Be brief."
            )

        events = await _gather_speeches(agents, ctx, prompt_for, self.name)
        for e in events:
            yield e


class VerdictPhase:
    """Verdict phase is special: only the Oracle speaks, agents stay silent.
    The Session calls Oracle directly; this class exists to keep the FSM
    symmetric and for future custom verdict styles."""

    name = "verdict"

    async def run(self, agents, ctx):
        if False:  # pragma: no cover
            yield  # type: ignore[unreachable]
        return
