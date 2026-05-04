"""Discord sink — webhook post of the verdict + per-phase summary.

Uses a Discord webhook URL (Server Settings → Integrations → Webhooks).
Per Discord rate limits, posts are throttled and consolidated rather
than firing one webhook per speech.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from pantheon.types.events import (
    PhaseBoundaryEvent,
    SpeechEvent,
    SystemEvent,
    VerdictEvent,
)
from pantheon.types.verdict import Verdict

log = logging.getLogger("pantheon-bridges.discord")


@dataclass
class DiscordSink:
    webhook_url: str
    name: str = "discord"
    flush_per_phase: bool = True
    summary_max_chars: int = 1800

    _http: object = field(default=None, init=False)
    _phase_buffer: list[str] = field(default_factory=list, init=False)
    _last_phase: str = field(default="", init=False)

    async def _client(self):
        if self._http is not None:
            return self._http
        try:
            import httpx
        except ImportError as e:
            raise ImportError(
                "DiscordSink requires the [discord] extra. "
                "Install: `pip install pantheon-bridges[discord]`"
            ) from e
        self._http = httpx.AsyncClient(timeout=20)
        return self._http

    async def _post(self, content: str) -> None:
        client = await self._client()
        try:
            r = await client.post(
                self.webhook_url,
                json={"content": content[:2000]},
            )
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            log.warning("discord webhook failed: %s", e)
        # Discord per-webhook rate limit ~5 req/2s; be conservative.
        await asyncio.sleep(0.6)

    async def _flush_phase(self) -> None:
        if not self._phase_buffer:
            return
        text = "\n".join(self._phase_buffer)[: self.summary_max_chars]
        await self._post(f"**── {self._last_phase} ──**\n{text}")
        self._phase_buffer.clear()

    async def handle(self, event) -> None:
        if isinstance(event, SpeechEvent):
            self._last_phase = event.phase
            self._phase_buffer.append(
                f"**seat {event.seat} | {event.persona_id}**\n{event.text[:600]}"
            )
        elif isinstance(event, PhaseBoundaryEvent):
            if self.flush_per_phase:
                await self._flush_phase()
        elif isinstance(event, SystemEvent):
            self._phase_buffer.append(f"_[{event.role}] {event.message[:300]}_")
        elif isinstance(event, VerdictEvent):
            if self.flush_per_phase:
                await self._flush_phase()

    async def finalize(self, verdict: Verdict) -> None:
        if self._phase_buffer:
            await self._flush_phase()
        lines = [f"**VERDICT** — {verdict.question}"]
        for c in verdict.consensus:
            lines.append(f"• {c.statement[:400]}")
        if verdict.action_items:
            lines.append("\n**Actions:**")
            for a in verdict.action_items:
                lines.append(f"• {a.action[:300]}")
        await self._post("\n".join(lines))
        client = self._http
        if client is not None and hasattr(client, "aclose"):
            await client.aclose()  # type: ignore[func-returns-value]
