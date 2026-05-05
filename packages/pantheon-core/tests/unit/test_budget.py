"""BudgetGuard — hard limits raise before mutating state."""
from __future__ import annotations

import pytest
from pantheon import BudgetExceeded, BudgetGuard


def test_max_calls_breach():
    g = BudgetGuard(max_calls=2)
    g.check()
    g.record(0.001)
    g.check()
    g.record(0.001)
    with pytest.raises(BudgetExceeded):
        g.check()


def test_max_usd_breach():
    g = BudgetGuard(max_usd=0.005)
    g.record(0.004)
    g.check()
    g.record(0.002)
    with pytest.raises(BudgetExceeded):
        g.check()


def test_reset_clears_state():
    g = BudgetGuard(max_calls=1)
    g.record(0.0)
    with pytest.raises(BudgetExceeded):
        g.check()
    g.reset()
    g.check()  # ok now


def test_remaining_keys():
    g = BudgetGuard()
    r = g.remaining()
    assert {"usd", "calls", "minutes"}.issubset(r.keys())
