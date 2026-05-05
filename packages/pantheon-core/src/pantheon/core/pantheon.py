"""Pantheon — top-level coordinator. The user-facing entry point.

```python
from pantheon import Pantheon, MockGateway

p = Pantheon(gateway=MockGateway())
p.summon(["confucius", "socrates", "naval"])
verdict = await p.debate("Should I quit?", rounds=3).run()
```

A Pantheon instance owns:
  - A persona registry view (defaults to the global `registry`)
  - A Gateway (or one default Gateway shared by all Models)
  - Per-agent overrides (model, instance suffix)
  - A BudgetGuard, configurable per-debate or globally
"""
from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from pantheon.core.agent import Agent
from pantheon.core.model import Model
from pantheon.core.persona import registry as global_registry
from pantheon.debate.session import Session, make_debate_id
from pantheon.gateway.base import Gateway
from pantheon.gateway.mock import MockGateway
from pantheon.gateway.replay import ReplayGateway
from pantheon.obs.budget import BudgetGuard
from pantheon.obs.replay import Recorder, default_session_dir
from pantheon.roles.auditor import Auditor
from pantheon.roles.moderator import Moderator
from pantheon.roles.oracle import Oracle


@dataclass
class Pantheon:
    gateway: Gateway = field(default_factory=MockGateway)
    budget: BudgetGuard = field(default_factory=BudgetGuard)
    persona_conflict: str = "warn"  # "allow" | "warn" | "error"
    record_sessions: bool = True
    sessions_dir: Path | None = None

    agents: list[Agent] = field(default_factory=list)
    moderator: Moderator = field(default_factory=Moderator)
    oracle: Oracle = field(default_factory=Oracle)
    auditor: Auditor = field(default_factory=Auditor)
    user_weights: dict[int, float] = field(default_factory=dict)

    # ---------- agent management ----------

    @classmethod
    def summon(
        cls,
        persona_ids: list[str],
        *,
        gateway: Gateway | None = None,
        default_model: str | None = None,
        budget: BudgetGuard | None = None,
    ) -> Pantheon:
        """Convenience: build a Pantheon and add one Agent per persona id.
        Each persona's `model_preference.primary` is used unless overridden."""
        p = cls(
            gateway=gateway or MockGateway(),
            budget=budget or BudgetGuard(),
        )
        for i, pid in enumerate(persona_ids, start=1):
            persona = global_registry.get(pid)
            model_id = default_model or persona.spec.model_preference.primary
            p.add_agent(Agent(seat=i, persona=persona, model=Model(id=model_id, gateway=p.gateway)))
        return p

    def add_agent(self, agent: Agent) -> None:
        if len(self.agents) >= 10:
            raise ValueError("Pantheon has a hard limit of 10 seats.")
        # persona conflict check
        existing_ids = [a.persona.id for a in self.agents]
        if agent.persona.id in existing_ids:
            others = [a for a in self.agents if a.persona.id == agent.persona.id]
            if self.persona_conflict == "error":
                raise ValueError(
                    f"persona {agent.persona.id} already worn by seat "
                    f"{others[0].seat}; persona_conflict='error'"
                )
            # auto-assign instance suffixes for disambiguation
            agent.instance_suffix = str(len(others) + 1)
            if self.persona_conflict == "warn":
                # Annotate; callers may inspect agent.swap_log entry created later.
                pass
            # Also retroactively suffix the first instance if it has none.
            if not others[0].instance_suffix:
                others[0].instance_suffix = "1"
        if any(a.seat == agent.seat for a in self.agents):
            raise ValueError(f"seat {agent.seat} already occupied")
        self.agents.append(agent)

    def set_weight(
        self,
        *,
        seat: int | None = None,
        persona: str | None = None,
        weight: float,
    ) -> None:
        if (seat is None) == (persona is None):
            raise ValueError("specify exactly one of seat= or persona=")
        if seat is not None:
            self.user_weights[seat] = weight
        else:
            for a in self.agents:
                if a.persona.id == persona:
                    self.user_weights[a.seat] = weight

    def set_all_models(self, model_id: str) -> None:
        for a in self.agents:
            a.model = Model(id=model_id, gateway=self.gateway)

    # ---------- debate factory ----------

    def debate(
        self,
        question: str,
        *,
        rounds: int = 3,
        topic_tags: dict[str, float] | None = None,
        seed: int | None = None,
        budget: BudgetGuard | None = None,
        record: bool | None = None,
        replay_from: str | Path | None = None,
    ) -> Session:
        """Construct a Session. The session is **not** running yet — call
        `await session.run()` or iterate `session.stream()`."""
        if not self.agents:
            raise RuntimeError("no agents added; call summon() or add_agent() first")
        debate_id = make_debate_id(question, self.agents, seed)
        session_id = uuid.uuid4().hex
        b = budget or self.budget
        # If replaying, swap each agent's gateway-backed model for a ReplayGateway.
        if replay_from is not None:
            replay_gw = ReplayGateway(replay_from, fallback=self.gateway)
            for a in self.agents:
                a.model = Model(id=a.model.id, gateway=replay_gw)
        rec = None
        if record is None:
            record = self.record_sessions
        if record:
            sdir = self.sessions_dir or default_session_dir()
            sdir.mkdir(parents=True, exist_ok=True)
            rec = Recorder(sdir / f"{debate_id}.jsonl", debate_id=debate_id)
            rec.write(
                "session_open",
                debate_id=debate_id,
                question=question,
                seed=seed,
                agents=[
                    {"seat": a.seat, "persona": a.persona.id, "model": a.model.id}
                    for a in self.agents
                ],
            )
        return Session(
            session_id=session_id,
            debate_id=debate_id,
            question=question,
            agents=self.agents,
            moderator=self.moderator,
            oracle=self.oracle,
            auditor=self.auditor,
            budget=b,
            recorder=rec,
            topic_tags=topic_tags or {},
            user_weights=dict(self.user_weights),
            rounds=rounds,
            seed=seed,
        )


# Convenience: a sync wrapper for trivial scripts.
def quick_debate(
    persona_ids: list[str],
    question: str,
    *,
    rounds: int = 3,
    gateway: Gateway | None = None,
):
    """Synchronous one-liner: returns the Verdict. Spins up its own loop."""
    import asyncio

    async def _go():
        p = Pantheon.summon(persona_ids, gateway=gateway)
        return await p.debate(question, rounds=rounds).run()

    return asyncio.run(_go())


# Re-import to avoid circular import warnings on type-checkers.
_ = secrets
