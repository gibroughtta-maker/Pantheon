"""End-to-end calibration: L2-only mode + L2+L4 hybrid + replay determinism."""
from __future__ import annotations

import pytest
from pantheon import MockGateway, Model, ScriptedReply, registry
from pantheon.calibration.probes import DIMENSIONS, load_probes
from pantheon.calibration.runner import run_calibration


@pytest.mark.asyncio
async def test_l2_only_mode_when_no_judges(tmp_path):
    target = registry.get("confucius")  # has corpus loaded
    res = await run_calibration(
        target, anchor_personas=[], judges=[], record_dir=tmp_path
    )
    assert res.method == "l2_only"
    assert res.l4 is None
    assert set(res.final.keys()) == set(DIMENSIONS)
    # Confucius corpus actually covers ethics → should be > 0
    assert res.final["ethics"] > 0.0
    # σ defined only for L2 vs L4 disagreement; in L2-only mode all σ = 0.
    for dim in DIMENSIONS:
        assert res.sigma[dim] == 0.0
    assert res.flags == []


@pytest.mark.asyncio
async def test_l2_l4_hybrid_full_run(tmp_path):
    target = registry.get("confucius")
    anchor = registry.get("socrates")
    gw = MockGateway()
    # Prefill enough scripted replies for the full pairwise tournament.
    n_calls = len(DIMENSIONS) * len(load_probes().for_dimension("ethics")) * 1 * 1
    for _ in range(n_calls):
        gw.add_reply(ScriptedReply(text="VOTE: A\nconfucius wins this exchange.",
                                   model_id="judge-mock"))
    res = await run_calibration(
        target,
        anchor_personas=[anchor],
        judges=[Model(id="judge-mock", gateway=gw)],
        record_dir=tmp_path,
        seed=42,
    )
    assert res.method == "l2_l4_hybrid"
    assert res.l4 is not None
    # Recording exists.
    assert res.recording_path
    from pathlib import Path
    assert Path(res.recording_path).exists()


@pytest.mark.asyncio
async def test_replay_determinism(tmp_path):
    """Same seed + same scripted gateway → identical final scores."""
    target = registry.get("confucius")
    anchor = registry.get("socrates")

    async def _one_run() -> dict[str, float]:
        gw = MockGateway()
        n_calls = len(DIMENSIONS) * 6 * 1 * 1
        for i in range(n_calls):
            # Deterministic vote pattern: A wins on even probes, B on odd.
            vote = "A" if i % 2 == 0 else "B"
            gw.add_reply(ScriptedReply(text=f"VOTE: {vote}\nrationale.",
                                       model_id="judge-mock"))
        res = await run_calibration(
            target,
            anchor_personas=[anchor],
            judges=[Model(id="judge-mock", gateway=gw)],
            record_dir=tmp_path,
            seed=99,
        )
        return res.final

    a = await _one_run()
    b = await _one_run()
    assert a == b, f"calibration not deterministic:\n{a}\n  vs\n{b}"


@pytest.mark.asyncio
async def test_sigma_flags_when_l2_l4_disagree(tmp_path):
    """If we set up L4 to vote always-A and a corpus that gives near-zero L2
    score on most dims, we expect |L2 − L4| to be large on some dims and
    they should be flagged for manual review."""
    # Use a persona without rich corpus so L2 ≈ 0 across many dims.
    target = registry.get("naval")  # naval has no corpus dir at all
    anchor = registry.get("confucius")
    gw = MockGateway()
    n_calls = len(DIMENSIONS) * 6 * 1 * 1
    for _ in range(n_calls):
        # naval (target = A) always wins → L4 will be high, but L2 will be 0.
        gw.add_reply(ScriptedReply(text="VOTE: A\nnaval wins.",
                                   model_id="judge-mock"))
    res = await run_calibration(
        target,
        anchor_personas=[anchor],
        judges=[Model(id="judge-mock", gateway=gw)],
        record_dir=tmp_path,
        seed=1,
        sigma_threshold=0.2,
    )
    # At least one dim should be flagged because L4 ≫ L2 = 0.
    assert len(res.flags) >= 1, f"expected ≥1 flag; got {res.flags} with σ={res.sigma}"
