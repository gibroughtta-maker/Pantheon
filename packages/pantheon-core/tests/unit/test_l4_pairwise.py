"""L4 pairwise scorer + Bradley-Terry math."""
from __future__ import annotations

import pytest
from pantheon import MockGateway, Model, ScriptedReply, registry
from pantheon.calibration.l4_pairwise import (
    _anchor_to_unit,
    _bradley_terry,
    _parse_vote,
    score_l4,
)
from pantheon.calibration.probes import load_probes


def test_parse_vote_each_format():
    assert _parse_vote("VOTE: A\nrationale here")[0] == "A"
    assert _parse_vote("vote: B")[0] == "B"
    assert _parse_vote("VOTE: TIE\nthey are equal")[0] == "tie"
    # Plain "A" or "B" at end-of-first-line counts.
    assert _parse_vote("Reasoning... so the answer is A")[0] == "A"


def test_bradley_terry_consistent_winner():
    # If A beats B 10-0 and beats C 10-0, A's theta should be highest.
    counts = {
        ("A", "B"): 10, ("B", "A"): 0,
        ("A", "C"): 10, ("C", "A"): 0,
        ("B", "C"): 5,  ("C", "B"): 5,
    }
    theta = _bradley_terry(counts, ["A", "B", "C"])
    assert theta["A"] > theta["B"]
    assert theta["A"] > theta["C"]
    # B and C should be roughly equal (they tied each other).
    assert abs(theta["B"] - theta["C"]) < 0.5


def test_anchor_to_unit_two_anchors_linear():
    theta = {"target": 1.5, "anchor_low": 0.5, "anchor_high": 2.5}
    anchor_scores = {"anchor_low": 0.2, "anchor_high": 0.8}
    unit = _anchor_to_unit(theta, anchor_scores)
    # target sits at the midpoint of anchors, so unit ≈ 0.5.
    assert 0.4 < unit["target"] < 0.6
    # Endpoints map back to known scores.
    assert abs(unit["anchor_low"] - 0.2) < 0.01
    assert abs(unit["anchor_high"] - 0.8) < 0.01


def test_anchor_to_unit_no_anchor_falls_back_minmax():
    theta = {"a": 1.0, "b": 2.0, "c": 0.5}
    unit = _anchor_to_unit(theta, {})
    assert unit["b"] == 1.0
    assert unit["c"] == 0.0


@pytest.mark.asyncio
async def test_score_l4_target_winning_all_dims():
    """Scripted gateway: target always wins. Expect target's L4 score ≥ 0.5
    and ≥ anchor's known scores."""
    probes = load_probes()
    target = registry.get("confucius")
    anchor = registry.get("naval")
    gw = MockGateway()
    # Force every judge call to vote "VOTE: A" (target wins).
    # Add many scripted replies — one per probe call. The mock falls back
    # to fallback template if queue is empty, which won't say VOTE: A,
    # so we add enough.
    n_dims = 7
    n_probes_per_dim = 6
    n_anchors = 1
    n_judges = 1
    total_calls = n_dims * n_probes_per_dim * n_anchors * n_judges
    for _ in range(total_calls):
        gw.add_reply(ScriptedReply(text="VOTE: A\ntarget is stronger here.",
                                   model_id="judge-mock"))
    res = await score_l4(target, [anchor], probes, [Model(id="judge-mock", gateway=gw)], seed=0)
    for dim in res.by_dimension:
        # Target has won every comparison → final score ≥ anchor's known.
        assert res.by_dimension[dim].score >= 0.0
        wr = res.by_dimension[dim].win_rate_vs_anchors[anchor.id]
        assert wr == pytest.approx(1.0)
