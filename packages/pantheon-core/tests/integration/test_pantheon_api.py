"""Pantheon top-level API: summon, add_agent, persona conflict, hard limits."""
from __future__ import annotations

import pytest

from pantheon import Agent, MockGateway, Model, Pantheon, registry


def test_summon_creates_three_agents():
    p = Pantheon.summon(["confucius", "socrates", "naval"], gateway=MockGateway())
    assert [a.seat for a in p.agents] == [1, 2, 3]
    assert [a.persona.id for a in p.agents] == ["confucius", "socrates", "naval"]


def test_seat_collision_raises():
    p = Pantheon(gateway=MockGateway())
    p.add_agent(
        Agent(seat=1, persona=registry.get("confucius"),
              model=Model(id="x", gateway=p.gateway))
    )
    with pytest.raises(ValueError):
        p.add_agent(
            Agent(seat=1, persona=registry.get("socrates"),
                  model=Model(id="y", gateway=p.gateway))
        )


def test_max_ten_seats():
    p = Pantheon(gateway=MockGateway())
    for i in range(1, 11):
        p.add_agent(
            Agent(
                seat=i,
                persona=registry.get("confucius"),
                model=Model(id="x", gateway=p.gateway),
            )
        )
    with pytest.raises(ValueError):
        p.add_agent(
            Agent(seat=11, persona=registry.get("naval"),
                  model=Model(id="x", gateway=p.gateway))
        )


def test_persona_conflict_warn_assigns_instance_suffix():
    p = Pantheon(gateway=MockGateway(), persona_conflict="warn")
    p.add_agent(
        Agent(seat=1, persona=registry.get("confucius"),
              model=Model(id="x", gateway=p.gateway))
    )
    p.add_agent(
        Agent(seat=2, persona=registry.get("confucius"),
              model=Model(id="x", gateway=p.gateway))
    )
    # Both agents got disambiguating suffixes:
    assert p.agents[0].instance_suffix == "1"
    assert p.agents[1].instance_suffix == "2"


def test_persona_conflict_error_raises():
    p = Pantheon(gateway=MockGateway(), persona_conflict="error")
    p.add_agent(
        Agent(seat=1, persona=registry.get("confucius"),
              model=Model(id="x", gateway=p.gateway))
    )
    with pytest.raises(ValueError):
        p.add_agent(
            Agent(seat=2, persona=registry.get("confucius"),
                  model=Model(id="x", gateway=p.gateway))
        )


def test_set_weight_by_seat():
    p = Pantheon.summon(["confucius", "socrates"], gateway=MockGateway())
    p.set_weight(seat=1, weight=2.0)
    assert p.user_weights == {1: 2.0}


def test_set_weight_by_persona_id():
    p = Pantheon.summon(["confucius", "socrates"], gateway=MockGateway())
    p.set_weight(persona="socrates", weight=0.5)
    assert p.user_weights == {2: 0.5}


def test_set_all_models_overrides():
    p = Pantheon.summon(["confucius", "socrates"], gateway=MockGateway())
    p.set_all_models("claude-opus-4-7")
    assert all(a.model.id == "claude-opus-4-7" for a in p.agents)
