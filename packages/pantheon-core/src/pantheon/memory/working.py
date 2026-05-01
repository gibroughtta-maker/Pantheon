"""Working memory — per-agent conversation history within a single debate.

History is preserved across `swap_persona` (relay mode); a new persona inherits
the full transcript and is expected to begin with a handoff statement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str
    persona_id: str | None = None  # which persona generated this assistant turn
    phase: str | None = None       # phase tag for replay/audit


@dataclass
class WorkingMemory:
    """Per-agent transcript. Lives for one debate."""

    seat: int
    history: list[Message] = field(default_factory=list)

    def append(self, msg: Message) -> None:
        self.history.append(msg)

    def render_for_llm(self, system_prompt: str) -> list[dict[str, str]]:
        """Render history as a chat-completion message list with the current
        persona's system prompt prepended. Older system messages from previous
        personas are demoted to assistant context so the new persona sees what
        was said but doesn't get conflicting instructions."""
        out: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for m in self.history:
            if m.role == "system":
                # demoted: previous persona's system note → user-side context
                out.append({"role": "user", "content": f"[earlier framing]\n{m.content}"})
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    def speech_count(self) -> int:
        return sum(1 for m in self.history if m.role == "assistant")
