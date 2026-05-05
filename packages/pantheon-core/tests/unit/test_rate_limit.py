"""Token-bucket rate limiter."""
from __future__ import annotations

import asyncio
import time

import pytest
from pantheon.gateway.rate_limit import RateLimiter


@pytest.mark.asyncio
async def test_unconfigured_model_does_not_block():
    rl = RateLimiter()
    waited = await rl.acquire("not-configured", est_tokens=10000)
    assert waited == 0.0


@pytest.mark.asyncio
async def test_within_limits_no_wait():
    rl = RateLimiter()
    rl.configure("m", rpm=60, tpm=60_000)
    waited = await rl.acquire("m", est_tokens=100)
    assert waited == 0.0


@pytest.mark.asyncio
async def test_rpm_blocks_when_burst_exhausted():
    rl = RateLimiter()
    # Tight RPM: 12 per minute → bucket capacity 12.
    rl.configure("m", rpm=12, tpm=1_000_000)
    # Drain the bucket.
    for _ in range(12):
        await rl.acquire("m", est_tokens=10)
    # 13th call must wait some non-trivial amount.
    t0 = time.monotonic()
    await asyncio.wait_for(rl.acquire("m", est_tokens=10), timeout=8.0)
    elapsed = time.monotonic() - t0
    # Refill rate is 12/60 = 0.2/sec; at least ~5s for 1 token.
    # We use a loose bound — 1+ seconds proves it blocked.
    assert elapsed > 1.0


@pytest.mark.asyncio
async def test_credit_returns_unused_tokens():
    rl = RateLimiter()
    rl.configure("m", rpm=10, tpm=1000)
    # Reserve 1000 estimated, use only 100.
    await rl.acquire("m", est_tokens=1000)
    s_before = rl.status("m")
    # Most/all of TPM should now be ~0 remaining.
    assert s_before["tpm_remaining"] < 50
    rl.credit("m", actual_tokens=100, est_tokens=1000)
    s_after = rl.status("m")
    assert s_after["tpm_remaining"] >= 800


def test_status_for_unknown_returns_inf():
    rl = RateLimiter()
    s = rl.status("nope")
    assert s["rpm_remaining"] == float("inf")


@pytest.mark.asyncio
async def test_reconfigure_resets_buckets():
    rl = RateLimiter()
    rl.configure("m", rpm=2, tpm=1000)
    await rl.acquire("m", est_tokens=10)
    await rl.acquire("m", est_tokens=10)  # bucket now empty
    rl.configure("m", rpm=10, tpm=1000)   # reset to full capacity
    s = rl.status("m")
    assert s["rpm_remaining"] >= 9
