"""Model — stateless wrapper that pairs a model id with a Gateway."""
from __future__ import annotations

from dataclasses import dataclass

from pantheon.gateway.base import CallResult, Gateway


@dataclass
class Model:
    id: str
    gateway: Gateway
    rpm_limit: int = 60
    tpm_limit: int = 200_000

    async def call(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        seed: int | None = None,
    ) -> CallResult:
        if not self.gateway.supports(self.id):
            raise ValueError(f"gateway does not support model {self.id!r}")
        return await self.gateway.call(
            self.id,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
        )
