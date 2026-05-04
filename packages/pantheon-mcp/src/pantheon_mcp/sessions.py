"""In-process session manager for the MCP server.

Sessions are referenced by ``session_id`` (returned from ``summon``).
A session is a Pantheon instance plus the active debate Session (if
``debate`` has been called). State is non-persistent — process restart
loses sessions, but the JSONL recordings on disk let any debate be
replayed by id.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Any

from pantheon import (
    Agent,
    BudgetGuard,
    Gateway,
    MockGateway,
    Model,
    OpenClawGateway,
    Pantheon,
    registry,
)
from pantheon.debate.session import Session


@dataclass
class _SessionRecord:
    pantheon_id: str
    pantheon: Pantheon
    debate: Session | None = None
    created_at: float = 0.0


@dataclass
class SessionManager:
    """Holds the active pantheon sessions for the MCP server."""

    gateway: Gateway = field(default_factory=MockGateway)
    sessions: dict[str, _SessionRecord] = field(default_factory=dict)

    def summon(self, persona_ids: list[str]) -> str:
        if not persona_ids:
            raise ValueError("persona_ids must be non-empty")
        if len(persona_ids) > 10:
            raise ValueError("Pantheon has a hard limit of 10 seats")
        # Validate before allocating a session id.
        for pid in persona_ids:
            registry.get(pid)
        sid = uuid.uuid4().hex
        p = Pantheon(gateway=self.gateway, budget=BudgetGuard())
        for i, pid in enumerate(persona_ids, start=1):
            persona = registry.get(pid)
            model_id = persona.spec.model_preference.primary
            p.add_agent(Agent(seat=i, persona=persona, model=Model(id=model_id, gateway=p.gateway)))
        self.sessions[sid] = _SessionRecord(pantheon_id=sid, pantheon=p)
        return sid

    def get(self, session_id: str) -> _SessionRecord:
        if session_id not in self.sessions:
            raise KeyError(f"unknown session_id {session_id!r}")
        return self.sessions[session_id]

    def start_debate(
        self,
        session_id: str,
        question: str,
        rounds: int = 3,
        seed: int | None = None,
    ) -> Session:
        rec = self.get(session_id)
        if rec.debate is not None:
            raise ValueError(
                f"session {session_id} already has a debate; use a new session"
            )
        rec.debate = rec.pantheon.debate(question, rounds=rounds, seed=seed)
        return rec.debate

    def queue_swap_persona(self, session_id: str, seat: int, to_persona: str) -> None:
        rec = self.get(session_id)
        if rec.debate is None:
            raise ValueError("call debate() before swapping")
        persona = registry.get(to_persona)
        rec.debate.queue_swap_persona(seat=seat, to_persona=persona)

    def queue_swap_model(self, session_id: str, seat: int, to_model: str) -> None:
        rec = self.get(session_id)
        if rec.debate is None:
            raise ValueError("call debate() before swapping")
        rec.debate.queue_swap_model(
            seat=seat, to_model=Model(id=to_model, gateway=self.gateway)
        )


def gateway_from_env() -> Gateway:
    """Build the right gateway from environment.

    PANTHEON_GATEWAY=mock     → MockGateway (default; safe)
    PANTHEON_GATEWAY=openclaw → OpenClawGateway from OPENCLAW_BASE_URL/KEY
    """
    name = (os.environ.get("PANTHEON_GATEWAY") or "mock").lower()
    if name == "openclaw":
        base = os.environ["OPENCLAW_BASE_URL"]
        key = os.environ.get("OPENCLAW_API_KEY")
        project = os.environ.get("OPENCLAW_PROJECT")
        return OpenClawGateway(base_url=base, api_key=key, project=project)
    return MockGateway()
