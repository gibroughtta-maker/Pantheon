"""Weight system — softmax-of-logs sums to 1, handles zeros, respects user prefs."""
from __future__ import annotations

import pytest

from pantheon import Agent, MockGateway, Model, registry
from pantheon.core.weights import _cosine_like, compute_weights


def _agents(gateway):
    return [
        Agent(seat=1, persona=registry.get("confucius"),
              model=Model(id="deepseek-chat", gateway=gateway)),
        Agent(seat=2, persona=registry.get("socrates"),
              model=Model(id="claude-opus-4-7", gateway=gateway)),
        Agent(seat=3, persona=registry.get("naval"),
              model=Model(id="claude-opus-4-7", gateway=gateway)),
    ]


def test_weights_sum_to_one():
    gw = MockGateway()
    w = compute_weights(_agents(gw), {"ethics": 0.9, "business": 0.7})
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_weights_uniform_when_no_topic():
    gw = MockGateway()
    w = compute_weights(_agents(gw), {})
    assert abs(sum(w.values()) - 1.0) < 1e-9
    # All seats present:
    assert set(w.keys()) == {1, 2, 3}


def test_user_pref_increases_weight():
    gw = MockGateway()
    w_default = compute_weights(_agents(gw), {"ethics": 0.5})
    w_boosted = compute_weights(_agents(gw), {"ethics": 0.5}, user_prefs={1: 5.0})
    assert w_boosted[1] > w_default[1]


def test_business_topic_favors_naval():
    gw = MockGateway()
    w = compute_weights(_agents(gw), {"business": 1.0, "technology": 0.8})
    # Naval has high business+tech skills; should outweigh Confucius for this topic
    assert w[3] > w[1]


def test_cosine_like_bounded():
    assert 0.0 <= _cosine_like({"a": 1.0}, {"a": 1.0}) <= 1.0
    assert _cosine_like({}, {}) == 0.5
    assert _cosine_like({"a": 0.0}, {"a": 0.0}) == 0.5
