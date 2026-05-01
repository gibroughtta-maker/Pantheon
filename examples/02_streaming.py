"""Streaming — consume events as the debate runs."""
from __future__ import annotations

import asyncio

from pantheon import MockGateway, Pantheon
from pantheon.types.events import (
    PhaseBoundaryEvent,
    SpeechEvent,
    SwapEvent,
    SystemEvent,
    VerdictEvent,
)


async def main() -> None:
    p = Pantheon.summon(["confucius", "socrates", "naval"], gateway=MockGateway())
    sess = p.debate("Is moderation a virtue or a vice?", rounds=3, seed=1)
    async for ev in sess.stream():
        if isinstance(ev, SpeechEvent):
            print(f"[seat {ev.seat}|{ev.persona_id}|{ev.phase}] {ev.text[:120]}")
        elif isinstance(ev, PhaseBoundaryEvent):
            print(f"── {ev.from_phase} → {ev.to_phase}")
        elif isinstance(ev, SwapEvent):
            print(f"⚡ swap seat {ev.seat}: {ev.from_id} → {ev.to_id}")
        elif isinstance(ev, SystemEvent):
            print(f"[{ev.role}] {ev.message[:120]}")
        elif isinstance(ev, VerdictEvent):
            print(f"✓ verdict ready ({ev.debate_id})")
    v = await sess.verdict()
    print(f"\nrobustness={v.consensus_robustness}, "
          f"unverified_quotes={v.quality.unverified_quote_count}")


if __name__ == "__main__":
    asyncio.run(main())
