"""End-to-end debate runs with MockGateway. Asserts FSM completion,
event ordering, verdict shape, and idempotent debate_id."""
from __future__ import annotations

import pytest

from pantheon import MockGateway, Pantheon
from pantheon.types.events import (
    PhaseBoundaryEvent,
    SpeechEvent,
    SystemEvent,
    VerdictEvent,
)


@pytest.mark.asyncio
async def test_three_persona_debate_runs_to_verdict(pantheon_three: Pantheon):
    sess = pantheon_three.debate("Should I quit my job?", rounds=3, seed=1)
    events = [ev async for ev in sess.stream()]
    types = [type(e).__name__ for e in events]
    assert "PhaseBoundaryEvent" in types
    assert "SpeechEvent" in types
    assert "VerdictEvent" in types

    # Speech count: 3 personas × (opening + cross_exam + rebuttal + ≥1 synthesis) ≥ 12
    speeches = [e for e in events if isinstance(e, SpeechEvent)]
    assert len(speeches) >= 12

    v = await sess.verdict()
    assert v.session_id
    assert v.debate_id
    assert v.consensus, "verdict should produce at least one consensus point"
    assert len(v.speaker_summary) == 3
    assert v.cost.total_calls == v.model_calls


@pytest.mark.asyncio
async def test_seq_is_monotonic(pantheon_three: Pantheon):
    sess = pantheon_three.debate("Q?", rounds=3, seed=2)
    events = [ev async for ev in sess.stream()]
    seqs = [e.seq for e in events]
    assert seqs == sorted(seqs)
    assert len(seqs) == len(set(seqs)), "seq numbers must be unique"


@pytest.mark.asyncio
async def test_phase_order(pantheon_three: Pantheon):
    sess = pantheon_three.debate("Q?", rounds=3, seed=3)
    transitions = [
        (e.from_phase, e.to_phase)
        async for e in sess.stream()
        if isinstance(e, PhaseBoundaryEvent)
    ]
    expected_first = [
        ("created", "opening"),
        ("opening", "cross_exam"),
        ("cross_exam", "rebuttal"),
    ]
    assert transitions[: len(expected_first)] == expected_first
    # Should end with verdict → closed (or degraded, but not in this test)
    assert transitions[-1] == ("verdict", "closed")


@pytest.mark.asyncio
async def test_debate_id_deterministic(pantheon_three: Pantheon):
    sess1 = pantheon_three.debate("Q?", rounds=3, seed=42)
    sess2 = pantheon_three.debate("Q?", rounds=3, seed=42)
    assert sess1.debate_id == sess2.debate_id


@pytest.mark.asyncio
async def test_session_consumed_only_once(pantheon_three: Pantheon):
    sess = pantheon_three.debate("Q?", rounds=3, seed=4)
    _ = [ev async for ev in sess.stream()]
    with pytest.raises(RuntimeError):
        async for _ in sess.stream():
            pass
