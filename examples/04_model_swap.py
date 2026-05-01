"""Model swap — same persona, different LLM mid-debate."""
from __future__ import annotations

import asyncio

from pantheon import MockGateway, Model, Pantheon
from pantheon.types.events import PhaseBoundaryEvent, SwapEvent


async def main() -> None:
    gw = MockGateway()
    p = Pantheon.summon(["confucius", "socrates", "naval"], gateway=gw)

    sess = p.debate("Is humility a strength or a weakness in negotiation?", rounds=3)
    swapped = False
    async for ev in sess.stream():
        if isinstance(ev, PhaseBoundaryEvent) and ev.to_phase == "rebuttal" and not swapped:
            # Move Confucius (seat 1) from his configured deepseek to claude-opus-4-7.
            sess.queue_swap_model(seat=1, to_model=Model(id="claude-opus-4-7", gateway=gw))
            swapped = True
        elif isinstance(ev, SwapEvent):
            print(f"⚡ model swap seat {ev.seat}: {ev.from_id} → {ev.to_id}")

    v = await sess.verdict()
    print("\nCost by model:", v.cost.by_model)


if __name__ == "__main__":
    asyncio.run(main())
