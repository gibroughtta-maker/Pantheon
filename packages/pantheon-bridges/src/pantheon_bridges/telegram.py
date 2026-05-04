"""Telegram sink — push debate events to a chat or channel.

Requires the `[telegram]` extra. Uses Telegram's Bot API:
  POST https://api.telegram.org/bot{token}/sendMessage

Throttled to avoid hitting Telegram's per-chat rate limit (≈ 1 msg/sec
for the same chat). Speech events are posted, swaps are highlighted,
and the verdict is sent as one final summary message.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from pantheon.types.events import (
    PhaseBoundaryEvent,
    SpeechEvent,
    SwapEvent,
    SystemEvent,
    VerdictEvent,
)
from pantheon.types.verdict import Verdict

log = logging.getLogger("pantheon-bridges.telegram")
_API = "https://api.telegram.org"


@dataclass
class TelegramSink:
    bot_token: str
    chat_id: str
    name: str = "telegram"
    parse_mode: str = "MarkdownV2"
    min_interval_s: float = 1.05      # Telegram per-chat throttle
    speech_max_chars: int = 800

    _last_send_at: float = field(default=0.0, init=False)
    _http: object = field(default=None, init=False)

    async def _client(self):
        if self._http is not None:
            return self._http
        try:
            import httpx
        except ImportError as e:
            raise ImportError(
                "TelegramSink requires the [telegram] extra. "
                "Install: `pip install pantheon-bridges[telegram]`"
            ) from e
        self._http = httpx.AsyncClient(timeout=20)
        return self._http

    async def _send(self, text: str) -> None:
        client = await self._client()
        # Throttle.
        now = asyncio.get_event_loop().time()
        wait = max(0.0, self._last_send_at + self.min_interval_s - now)
        if wait > 0:
            await asyncio.sleep(wait)
        url = f"{_API}/bot{self.bot_token}/sendMessage"
        try:
            r = await client.post(url, json={
                "chat_id": self.chat_id,
                "text": text[:4096],
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": True,
            })
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            log.warning("telegram send failed: %s", e)
        self._last_send_at = asyncio.get_event_loop().time()

    @staticmethod
    def _md_escape(s: str) -> str:
        # MarkdownV2 reserved chars — escape with backslash
        for ch in r"_*[]()~`>#+-=|{}.!":
            s = s.replace(ch, "\\" + ch)
        return s

    async def handle(self, event) -> None:
        if isinstance(event, SpeechEvent):
            head = self._md_escape(f"[seat {event.seat} | {event.persona_id} | {event.phase}]")
            body = self._md_escape(event.text[: self.speech_max_chars])
            await self._send(f"*{head}*\n{body}")
        elif isinstance(event, PhaseBoundaryEvent):
            await self._send(self._md_escape(f"── {event.from_phase} → {event.to_phase} ──"))
        elif isinstance(event, SwapEvent):
            await self._send(self._md_escape(
                f"⚡ swap @ seat {event.seat}: {event.from_id} → {event.to_id}"
            ))
        elif isinstance(event, SystemEvent):
            await self._send(self._md_escape(f"[{event.role}] {event.message[:600]}"))
        elif isinstance(event, VerdictEvent):
            await self._send(self._md_escape(f"✓ verdict ready ({event.debate_id})"))

    async def finalize(self, verdict: Verdict) -> None:
        lines = [f"*VERDICT* — {self._md_escape(verdict.question)}"]
        for c in verdict.consensus:
            lines.append(f"• {self._md_escape(c.statement[:300])}")
        if verdict.action_items:
            lines.append("\n*Actions:*")
            for a in verdict.action_items:
                lines.append(f"  • {self._md_escape(a.action[:300])}")
        await self._send("\n".join(lines))
        client = self._http
        if client is not None and hasattr(client, "aclose"):
            await client.aclose()  # type: ignore[func-returns-value]
