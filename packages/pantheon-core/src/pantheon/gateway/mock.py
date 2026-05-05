"""MockGateway — deterministic, no-network gateway for tests and demos.

Two modes:
  1. ``ScriptedReply`` queue per (model_id, persona_id) — exact replies.
  2. Fallback echo template if the queue is empty.

This is what every unit/integration test uses, and what `pantheon replay`
falls back to when no recorded session is available.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass

from pantheon.gateway.base import CallResult, Gateway


@dataclass
class ScriptedReply:
    """A pre-canned reply matched by (model_id, optional persona_id)."""

    text: str
    model_id: str
    persona_id: str | None = None
    cost_usd: float = 0.001
    prompt_tokens: int = 100
    completion_tokens: int = 50


class MockGateway(Gateway):
    """Deterministic gateway. Replies are popped FIFO from per-key queues."""

    def __init__(
        self,
        scripted: list[ScriptedReply] | None = None,
        *,
        fallback_template: str = "[mock {model}] Speaking as {persona}: I would say "
        "the question deserves careful thought; my view is shaped by my tradition.",
        latency_ms: int = 0,
    ) -> None:
        self._queues: dict[tuple[str, str | None], deque[ScriptedReply]] = defaultdict(deque)
        for r in scripted or []:
            self._queues[(r.model_id, r.persona_id)].append(r)
        self._fallback_template = fallback_template
        self._latency_ms = latency_ms
        self._lock = asyncio.Lock()
        self.calls: list[dict] = []

    def add_reply(self, reply: ScriptedReply) -> None:
        self._queues[(reply.model_id, reply.persona_id)].append(reply)

    def supports(self, model_id: str) -> bool:
        return True

    def _persona_id_from_messages(self, messages: list[dict[str, str]]) -> str | None:
        # The persona id is conventionally embedded in the system prompt as
        # `[persona:{id}]` so the mock can route replies. Real gateways ignore it.
        for m in messages:
            if m["role"] == "system" and "[persona:" in m["content"]:
                start = m["content"].index("[persona:") + len("[persona:")
                end = m["content"].index("]", start)
                return m["content"][start:end]
        return None

    async def call(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        seed: int | None = None,
    ) -> CallResult:
        if self._latency_ms:
            await asyncio.sleep(self._latency_ms / 1000)
        persona_id = self._persona_id_from_messages(messages)
        async with self._lock:
            key = (model_id, persona_id)
            q = self._queues.get(key) or self._queues.get((model_id, None))
            scripted = q.popleft() if q else None
            self.calls.append(
                {
                    "model_id": model_id,
                    "persona_id": persona_id,
                    "messages": messages,
                    "matched_scripted": scripted is not None,
                }
            )
        if scripted is not None:
            return CallResult(
                text=scripted.text,
                model_id=model_id,
                prompt_tokens=scripted.prompt_tokens,
                completion_tokens=scripted.completion_tokens,
                cost_usd=scripted.cost_usd,
            )
        return CallResult(
            text=self._fallback_template.format(model=model_id, persona=persona_id or "unknown"),
            model_id=model_id,
            prompt_tokens=80,
            completion_tokens=40,
            cost_usd=0.0001,
        )
