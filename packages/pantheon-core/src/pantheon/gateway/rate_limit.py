"""Token-bucket rate limiter per model.

Used by gateway implementations to honour ``Model.rpm_limit`` (requests
per minute) and ``Model.tpm_limit`` (tokens per minute). When a quota
would be breached, the limiter **awaits** rather than raising — so
callers see latency, not failure. This matches the v0.3 plan §8.5
("超限阻塞而非报错").

The limiter is async-safe; multiple concurrent ``acquire`` calls share
the same bucket. State is in-memory and per-process; a shared (multi-
process) limiter is a future M3 concern.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    """Generic token bucket. Refills at ``rate`` units per second up to
    ``capacity`` units."""

    capacity: float
    rate: float
    tokens: float = field(init=False)
    last: float = field(default_factory=time.monotonic, init=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.capacity)

    def _refill(self, now: float) -> None:
        elapsed = max(0.0, now - self.last)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last = now

    def time_to(self, n: float) -> float:
        """Seconds to wait until ``n`` tokens are available; 0 if already."""
        now = time.monotonic()
        self._refill(now)
        if self.tokens >= n:
            return 0.0
        deficit = n - self.tokens
        if self.rate <= 0:
            return float("inf")
        return deficit / self.rate

    def consume(self, n: float) -> None:
        now = time.monotonic()
        self._refill(now)
        self.tokens -= n  # may go negative briefly under concurrent contention


@dataclass
class _ModelLimits:
    rpm: _Bucket
    tpm: _Bucket


class RateLimiter:
    """Per-model RPM + TPM token bucket. Single instance shared across all
    gateways that route the same model through different surfaces."""

    def __init__(self) -> None:
        self._models: dict[str, _ModelLimits] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def configure(self, model_id: str, *, rpm: int, tpm: int) -> None:
        """Idempotently set the limits for a model. Reconfiguring resets buckets."""
        self._models[model_id] = _ModelLimits(
            rpm=_Bucket(capacity=float(rpm), rate=rpm / 60.0),
            tpm=_Bucket(capacity=float(tpm), rate=tpm / 60.0),
        )
        self._locks.setdefault(model_id, asyncio.Lock())

    def status(self, model_id: str) -> dict[str, float]:
        m = self._models.get(model_id)
        if not m:
            return {"rpm_remaining": float("inf"), "tpm_remaining": float("inf")}
        m.rpm._refill(time.monotonic())
        m.tpm._refill(time.monotonic())
        return {
            "rpm_remaining": round(m.rpm.tokens, 2),
            "tpm_remaining": round(m.tpm.tokens, 2),
            "rpm_capacity": m.rpm.capacity,
            "tpm_capacity": m.tpm.capacity,
        }

    async def acquire(self, model_id: str, *, est_tokens: int = 1000) -> float:
        """Block until 1 request and ``est_tokens`` tokens are available.

        Returns the seconds waited (0.0 if no wait was needed).
        """
        m = self._models.get(model_id)
        if not m:
            return 0.0
        lock = self._locks.setdefault(model_id, asyncio.Lock())
        waited = 0.0
        async with lock:
            while True:
                t_req = m.rpm.time_to(1)
                t_tok = m.tpm.time_to(est_tokens)
                t = max(t_req, t_tok)
                if t <= 0:
                    m.rpm.consume(1)
                    m.tpm.consume(est_tokens)
                    return waited
                # Sleep just past the deficit.
                await asyncio.sleep(t + 0.001)
                waited += t

    def credit(self, model_id: str, *, actual_tokens: int, est_tokens: int) -> None:
        """If actual < estimated, give back the difference."""
        m = self._models.get(model_id)
        if not m:
            return
        delta = est_tokens - actual_tokens
        if delta > 0:
            m.tpm.tokens = min(m.tpm.capacity, m.tpm.tokens + delta)


# Module-level default; gateway implementations may share it.
default_rate_limiter = RateLimiter()
