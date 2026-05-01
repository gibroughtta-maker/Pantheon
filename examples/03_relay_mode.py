"""Relay mode — swap a persona at a phase boundary.

Mid-debate we move seat 3 from Naval to Socrates: the new persona inherits
seat 3's transcript and opens with a handoff statement composed by the
framework (`pantheon.core.relay.compose_handoff`).
"""
from __future__ import annotations

import asyncio

from pantheon import MockGateway, Pantheon, registry
from pantheon.types.events import PhaseBoundaryEvent, SpeechEvent, SwapEvent


async def main() -> None:
    p = Pantheon.summon(["confucius", "socrates", "naval"], gateway=MockGateway())
    sess = p.debate("Should I take a buyout to focus on a side project?", rounds=3)

    # We'll queue a relay swap when the cross_exam phase begins. The swap is
    # applied at the next phase boundary, never mid-phase.
    queued = False
    async for ev in sess.stream():
        if isinstance(ev, PhaseBoundaryEvent):
            print(f"── {ev.from_phase} → {ev.to_phase}")
            if ev.to_phase == "rebuttal" and not queued:
                # Replace Naval (seat 3) with Confucius — let's see how a Confucius
                # in seat 3 (which has Naval's history) responds.
                sess.queue_swap_persona(
                    seat=3, to_persona=registry.get("confucius"), instance_suffix="2"
                )
                queued = True
        elif isinstance(ev, SwapEvent):
            print(f"⚡ {ev.kind} swap @ seat {ev.seat}: {ev.from_id} → {ev.to_id}")
            print(f"   handoff: {ev.handoff_statement!r}")
        elif isinstance(ev, SpeechEvent):
            print(f"[seat {ev.seat}|{ev.persona_id}|{ev.phase}] {ev.text[:120]}")

    v = await sess.verdict()
    print("\nRelay log:")
    for r in v.persona_relay_log:
        print(f"  seat {r.seat}: {r.from_persona} → {r.to_persona} (at {r.at_phase})")


if __name__ == "__main__":
    asyncio.run(main())
