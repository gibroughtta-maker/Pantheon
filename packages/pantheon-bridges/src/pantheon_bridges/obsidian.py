"""Obsidian sink — write the verdict as a markdown file in your vault."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pantheon.types.events import (
    PhaseBoundaryEvent,
    SpeechEvent,
    SwapEvent,
    SystemEvent,
    VerdictEvent,
)
from pantheon.types.verdict import Verdict


def _slug(text: str, maxlen: int = 50) -> str:
    s = re.sub(r"[^A-Za-z0-9一-鿿\s-]", "", text).strip()
    s = re.sub(r"\s+", "-", s)
    return s[:maxlen] or "debate"


@dataclass
class ObsidianSink:
    vault: str | os.PathLike            # ~/Vault
    folder: str = "Pantheon"            # subfolder under vault
    name: str = "obsidian"

    _events: list[str] = field(default_factory=list, init=False)
    _question: str = field(default="", init=False)
    _started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), init=False,
    )

    async def handle(self, event) -> None:
        if isinstance(event, SpeechEvent):
            self._events.append(
                f"### seat {event.seat} · {event.persona_id} ({event.phase})\n\n{event.text}\n"
            )
        elif isinstance(event, PhaseBoundaryEvent):
            self._events.append(f"---\n\n## {event.from_phase} → {event.to_phase}\n")
        elif isinstance(event, SwapEvent):
            self._events.append(
                f"> ⚡ swap @ seat {event.seat}: {event.from_id} → {event.to_id}\n"
            )
        elif isinstance(event, SystemEvent):
            self._events.append(f"> [{event.role}] {event.message}\n")
        elif isinstance(event, VerdictEvent):
            self._events.append(f"\n*verdict marker — debate {event.debate_id}*\n")

    async def finalize(self, verdict: Verdict) -> None:
        if not self._question:
            self._question = verdict.question
        slug = _slug(self._question)
        ts = self._started_at.strftime("%Y-%m-%d-%H%M")
        out_dir = Path(os.path.expanduser(str(self.vault))) / self.folder
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{ts}-{slug}.md"
        path.write_text(self._render(verdict), encoding="utf-8")

    def _render(self, v: Verdict) -> str:
        lines = [
            "---",
            f"debate_id: {v.debate_id}",
            f"trace_id: {v.trace_id}",
            f"date: {self._started_at.isoformat()}",
            f"robustness: {v.consensus_robustness}",
            f"no_consensus: {v.no_consensus}",
            "tags: [pantheon-debate]",
            "---",
            "",
            f"# {v.question}",
            "",
            "## Verdict",
            "",
            "### Consensus",
        ]
        for c in v.consensus:
            lines.append(f"- *(weight {c.weight:.2f}, {', '.join(c.supporters)})* {c.statement}")
        if v.minority_opinion:
            lines.append("\n### Minority")
            for m in v.minority_opinion:
                lines.append(f"- **{m.holder}**: {m.statement}")
        if v.action_items:
            lines.append("\n### Action items")
            for a in v.action_items:
                lines.append(f"- {a.action}")
        lines.append("\n### Quality")
        q = v.quality
        lines.append(f"- avg grounding: {q.avg_grounding_score}")
        lines.append(f"- unverified quotes: {q.unverified_quote_count}")
        lines.append(f"- devil's advocate: {q.devil_advocate_invoked}")
        if q.persona_swap_warnings:
            lines.append(f"- swap warnings: {q.persona_swap_warnings}")
        lines.append("\n## Transcript")
        lines.append("\n".join(self._events))
        lines.append("\n---\n")
        lines.append(f"*{v.disclaimer}*")
        return "\n".join(lines)
