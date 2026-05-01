"""Gateway base protocol.

Implementations must be **async** and **stateless across calls** (any rate-limit
state must be internally synchronized; the caller doesn't need to know).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class GatewayError(RuntimeError):
    """Raised when an LLM call fails irrecoverably (after retries)."""


@dataclass
class CallResult:
    text: str
    model_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    raw: dict = field(default_factory=dict)


class Gateway(Protocol):
    """The single shape every gateway implements."""

    async def call(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        seed: int | None = None,
    ) -> CallResult: ...

    def supports(self, model_id: str) -> bool: ...
