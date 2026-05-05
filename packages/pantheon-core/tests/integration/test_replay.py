"""Replay determinism — recording + ReplayGateway re-runs identically."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pantheon import Agent, MockGateway, Model, Pantheon, registry


def _build(gateway):
    p = Pantheon(gateway=gateway)
    for i, pid in enumerate(["confucius", "socrates", "naval"], start=1):
        persona = registry.get(pid)
        p.add_agent(
            Agent(
                seat=i,
                persona=persona,
                model=Model(id=persona.spec.model_preference.primary, gateway=gateway),
            )
        )
    return p


@pytest.mark.asyncio
async def test_replay_produces_same_debate_id(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("PANTHEON_SESSIONS_DIR", tmp)
        p1 = _build(MockGateway())
        v1 = await p1.debate("Q?", rounds=3, seed=99).run()
        recording = Path(tmp) / f"{v1.debate_id}.jsonl"
        assert recording.exists()

        p2 = _build(MockGateway())
        v2 = await p2.debate(
            "Q?", rounds=3, seed=99, replay_from=recording, record=False
        ).run()
        assert v1.debate_id == v2.debate_id


@pytest.mark.asyncio
async def test_recording_has_required_event_types(monkeypatch):
    import json

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("PANTHEON_SESSIONS_DIR", tmp)
        p = _build(MockGateway())
        v = await p.debate("Q?", rounds=3, seed=100).run()
        rec = Path(tmp) / f"{v.debate_id}.jsonl"
        rows = [json.loads(line) for line in rec.read_text().splitlines() if line.strip()]
        events = {r["event"] for r in rows}
        assert "session_open" in events
        assert "debate_event" in events
        assert "verdict" in events
