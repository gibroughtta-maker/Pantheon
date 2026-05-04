"""OpenAI-compatible gateway.

Works transparently against:
- OpenAI API
- Anthropic via OpenAI-compat shim
- DeepSeek
- OpenClaw gateway (which exposes /v1/chat/completions)
- NIM endpoints
- Local llama.cpp / vLLM servers

Cost is computed from a small model-pricing table; PRs welcome.
"""
from __future__ import annotations

import time

import httpx

from pantheon.gateway.base import CallResult, Gateway, GatewayError
from pantheon.gateway.rate_limit import RateLimiter

# Conservative public pricing per 1M tokens (input, output) in USD.
# Used only as best-effort cost accounting; override via models.local.yaml.
_PRICING_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-4-7": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (0.8, 4.0),
    "gpt-4o": (2.5, 10.0),
    "deepseek-chat": (0.27, 1.10),
}


class OpenAICompatibleGateway(Gateway):
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        *,
        timeout: float = 60.0,
        default_headers: dict[str, str] | None = None,
        model_allowlist: list[str] | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._headers = default_headers or {}
        self._allowlist = set(model_allowlist) if model_allowlist else None
        self._rate_limiter = rate_limiter

    def supports(self, model_id: str) -> bool:
        return self._allowlist is None or model_id in self._allowlist

    async def call(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        seed: int | None = None,
    ) -> CallResult:
        if not self.supports(model_id):
            raise GatewayError(f"model {model_id!r} not in allowlist")
        # RateLimiter blocks (not raises) when over quota — see plan §8.5.
        if self._rate_limiter is not None:
            est_tokens = sum(len(m["content"]) // 4 for m in messages) + max_tokens
            await self._rate_limiter.acquire(model_id, est_tokens=est_tokens)
        headers = dict(self._headers)
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload: dict = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if seed is not None:
            payload["seed"] = seed
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise GatewayError(f"gateway call failed: {e}") from e
        latency_ms = int((time.monotonic() - t0) * 1000)
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        pin = usage.get("prompt_tokens", 0)
        pout = usage.get("completion_tokens", 0)
        cost = self._cost(model_id, pin, pout)
        if self._rate_limiter is not None:
            actual = pin + pout
            est = sum(len(m["content"]) // 4 for m in messages) + max_tokens
            self._rate_limiter.credit(model_id, actual_tokens=actual, est_tokens=est)
        return CallResult(
            text=choice,
            model_id=model_id,
            prompt_tokens=pin,
            completion_tokens=pout,
            cost_usd=cost,
            latency_ms=latency_ms,
            raw=data,
        )

    @staticmethod
    def _cost(model_id: str, pin: int, pout: int) -> float:
        ip, op = _PRICING_USD_PER_MTOK.get(model_id, (0.0, 0.0))
        return (pin * ip + pout * op) / 1_000_000
