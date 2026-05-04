"""iching cast — determinism + structure."""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def pd(monkeypatch):
    import pantheon_divination
    p = importlib.reload(pantheon_divination)
    p.accept_disclaimer()
    return p


def test_64_hexagrams_loaded(pd):
    hxs = pd.iching.load_hexagrams()
    assert len(hxs) == 64
    # spot check
    assert hxs[1].chinese == "乾"
    assert hxs[2].chinese == "坤"
    assert hxs[64].chinese == "未濟"


def test_cast_deterministic(pd):
    a = pd.iching.cast(question="Should I quit?", seed=42)
    b = pd.iching.cast(question="Should I quit?", seed=42)
    assert a.structured["present_number"] == b.structured["present_number"]
    assert a.raw_state["throws"] == b.raw_state["throws"]
    assert a.raw_state["changing_indices"] == b.raw_state["changing_indices"]


def test_cast_changes_with_seed(pd):
    a = pd.iching.cast(question="?", seed=1)
    b = pd.iching.cast(question="?", seed=2)
    # Astronomically unlikely both produce identical throws.
    assert a.raw_state["throws"] != b.raw_state["throws"]


def test_cast_returns_six_lines(pd):
    r = pd.iching.cast(question="?", seed=42)
    assert len(r.lines) == 6
    for line in r.lines:
        assert "throw_value" in line.extra
        v = int(line.extra["throw_value"])
        assert v in (6, 7, 8, 9)


def test_changing_lines_produce_secondary(pd):
    # Find a seed that produces at least one changing line (should be common).
    for seed in range(20):
        r = pd.iching.cast(question="?", seed=seed)
        if r.raw_state["changing_indices"]:
            assert r.secondary
            assert r.structured["transformed_number"]
            return
    pytest.fail("no changing-line cast within 20 seeds — implausibly unlikely")


def test_no_changing_lines_no_secondary(pd):
    for seed in range(20):
        r = pd.iching.cast(question="?", seed=seed)
        if not r.raw_state["changing_indices"]:
            assert r.secondary == ""
            assert r.structured["transformed_number"] == ""
            return
    pytest.skip("could not find a no-changing cast within 20 seeds")
