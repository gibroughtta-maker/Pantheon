"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from pantheon import Agent, MockGateway, Model, Pantheon, registry


@pytest.fixture
def gateway() -> MockGateway:
    return MockGateway()


@pytest.fixture
def confucius_agent(gateway: MockGateway) -> Agent:
    return Agent(
        seat=1,
        persona=registry.get("confucius"),
        model=Model(id="deepseek-chat", gateway=gateway),
    )


@pytest.fixture
def socrates_agent(gateway: MockGateway) -> Agent:
    return Agent(
        seat=2,
        persona=registry.get("socrates"),
        model=Model(id="claude-opus-4-7", gateway=gateway),
    )


@pytest.fixture
def naval_agent(gateway: MockGateway) -> Agent:
    return Agent(
        seat=3,
        persona=registry.get("naval"),
        model=Model(id="claude-opus-4-7", gateway=gateway),
    )


@pytest.fixture
def pantheon_three(
    gateway: MockGateway, confucius_agent: Agent, socrates_agent: Agent, naval_agent: Agent
) -> Pantheon:
    p = Pantheon(gateway=gateway)
    p.add_agent(confucius_agent)
    p.add_agent(socrates_agent)
    p.add_agent(naval_agent)
    return p
