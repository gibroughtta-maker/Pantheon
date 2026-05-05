"""Relay mode and queue-based swap atomicity."""
from __future__ import annotations

import pytest
from pantheon import Pantheon, registry
from pantheon.types.events import PhaseBoundaryEvent, SwapEvent


@pytest.mark.asyncio
async def test_queued_persona_swap_applied_at_phase_boundary(pantheon_three: Pantheon):
    sess = pantheon_three.debate("Q?", rounds=3, seed=10)
    queued = False
    swap_seqs: list[int] = []
    boundary_seqs: list[int] = []
    async for ev in sess.stream():
        if isinstance(ev, PhaseBoundaryEvent):
            boundary_seqs.append(ev.seq)
            if ev.to_phase == "rebuttal" and not queued:
                sess.queue_swap_persona(seat=3, to_persona=registry.get("confucius"),
                                        instance_suffix="2")
                queued = True
        elif isinstance(ev, SwapEvent):
            swap_seqs.append(ev.seq)

    v = await sess.verdict()
    # Swap must have been emitted exactly once.
    assert len(swap_seqs) == 1
    # Relay log records the handoff.
    assert len(v.persona_relay_log) == 1
    rl = v.persona_relay_log[0]
    assert rl.seat == 3
    assert rl.from_persona.startswith("naval")
    assert rl.to_persona.startswith("confucius")


@pytest.mark.asyncio
async def test_handoff_statement_in_first_speech_after_swap(pantheon_three: Pantheon):
    from pantheon.types.events import SpeechEvent

    sess = pantheon_three.debate("Q?", rounds=3, seed=11)
    queued = False
    speeches_after_swap_seat3: list[str] = []
    swapped = False
    async for ev in sess.stream():
        if isinstance(ev, PhaseBoundaryEvent):
            if ev.to_phase == "rebuttal" and not queued:
                sess.queue_swap_persona(seat=3, to_persona=registry.get("confucius"))
                queued = True
        elif isinstance(ev, SwapEvent):
            swapped = True
        elif isinstance(ev, SpeechEvent) and swapped and ev.seat == 3:
            speeches_after_swap_seat3.append(ev.text)
    assert speeches_after_swap_seat3, "should have at least one speech after swap"
    # The first such speech must begin with the handoff statement.
    first = speeches_after_swap_seat3[0]
    assert "Taking the floor" in first or "先师" in first


@pytest.mark.asyncio
async def test_queued_model_swap_changes_model(pantheon_three: Pantheon):
    from pantheon import Model

    sess = pantheon_three.debate("Q?", rounds=3, seed=12)
    swapped = False
    async for ev in sess.stream():
        if isinstance(ev, PhaseBoundaryEvent) and ev.to_phase == "rebuttal" and not swapped:
            sess.queue_swap_model(seat=1, to_model=Model(id="gpt-4o", gateway=pantheon_three.gateway))
            swapped = True
    v = await sess.verdict()
    # gpt-4o should appear in cost.by_model (even with $0 mock cost it should be a key).
    assert "gpt-4o" in v.cost.by_model
