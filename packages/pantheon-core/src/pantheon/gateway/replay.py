"""ReplayGateway — feeds canned LLM responses from a recorded JSONL file.

Used by `pantheon replay <debate_id>` and by tests that pin to a known transcript.
The lookup key is `hash(model_id, messages)` — exact match required, otherwise
we fall through to a `fallback` gateway (defaults to error).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pantheon.gateway.base import CallResult, Gateway, GatewayError


def _key(model_id: str, messages: list[dict[str, str]]) -> str:
    h = hashlib.sha256()
    h.update(model_id.encode())
    for m in messages:
        h.update(b"\x00")
        h.update(m["role"].encode())
        h.update(b"\x00")
        h.update(m["content"].encode())
    return h.hexdigest()


class ReplayGateway(Gateway):
    def __init__(
        self,
        recording_path: str | Path,
        fallback: Gateway | None = None,
    ) -> None:
        self._path = Path(recording_path)
        self._cache: dict[str, CallResult] = {}
        self._fallback = fallback
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("event") != "llm_call":
                continue
            k = _key(row["model_id"], row["messages"])
            self._cache[k] = CallResult(
                text=row["text"],
                model_id=row["model_id"],
                prompt_tokens=row.get("prompt_tokens", 0),
                completion_tokens=row.get("completion_tokens", 0),
                cost_usd=row.get("cost_usd", 0.0),
                latency_ms=row.get("latency_ms", 0),
            )

    def supports(self, model_id: str) -> bool:
        return True

    async def call(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        seed: int | None = None,
    ) -> CallResult:
        k = _key(model_id, messages)
        hit = self._cache.get(k)
        if hit is not None:
            return hit
        if self._fallback is not None:
            return await self._fallback.call(
                model_id, messages, temperature=temperature, max_tokens=max_tokens, seed=seed
            )
        raise GatewayError(
            f"replay miss for model={model_id} key={k[:12]}…; no fallback configured"
        )
