"""Tarot deck + cast determinism."""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def pd(monkeypatch):
    import pantheon_divination
    p = importlib.reload(pantheon_divination)
    p.accept_disclaimer()
    return p


def test_78_cards_loaded(pd):
    cards = pd.tarot.load_cards()
    assert len(cards) == 78
    # 22 majors
    assert sum(1 for c in cards if c.arcana == "major") == 22
    # 14 per minor suit × 4
    for suit in ("wands", "cups", "swords", "pentacles"):
        assert sum(1 for c in cards if c.arcana == suit) == 14


def test_cast_celtic_cross_has_ten_positions(pd):
    r = pd.tarot.cast(question="Q?", spread="celtic_cross", seed=1)
    assert len(r.lines) == 10


def test_cast_three_card(pd):
    r = pd.tarot.cast(question="Q?", spread="three_card", seed=1)
    assert len(r.lines) == 3
    assert "Past" in r.lines[0].position


def test_cast_single(pd):
    r = pd.tarot.cast(question="Q?", spread="single", seed=1)
    assert len(r.lines) == 1


def test_cast_deterministic(pd):
    a = pd.tarot.cast(question="Q?", spread="celtic_cross", seed=99)
    b = pd.tarot.cast(question="Q?", spread="celtic_cross", seed=99)
    assert a.raw_state["drawn_card_ids"] == b.raw_state["drawn_card_ids"]
    assert a.raw_state["reversed_flags"] == b.raw_state["reversed_flags"]


def test_cast_no_card_repeats_in_one_spread(pd):
    r = pd.tarot.cast(question="Q?", spread="celtic_cross", seed=7)
    ids = r.raw_state["drawn_card_ids"]
    assert len(set(ids)) == len(ids)


def test_unknown_spread_raises(pd):
    with pytest.raises(ValueError, match="unknown spread"):
        pd.tarot.cast(question="?", spread="not-real", seed=1)


def test_cast_different_questions_different_results(pd):
    a = pd.tarot.cast(question="Q1", spread="single", seed=0)
    b = pd.tarot.cast(question="Q2", spread="single", seed=0)
    # Different question should usually give different draw (very likely).
    assert (a.raw_state["drawn_card_ids"] != b.raw_state["drawn_card_ids"]
            or a.raw_state["reversed_flags"] != b.raw_state["reversed_flags"])
