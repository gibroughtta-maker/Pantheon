"""Agent swap semantics — history preserved across persona swaps."""
from __future__ import annotations

import pytest
from pantheon import Agent, MockGateway, Model, ScriptedReply, registry
from pantheon.memory.working import Message


@pytest.mark.asyncio
async def test_swap_persona_preserves_history(gateway):
    a = Agent(
        seat=1,
        persona=registry.get("confucius"),
        model=Model(id="deepseek-chat", gateway=gateway),
    )
    a.memory.append(Message(role="user", content="Q1", phase="opening"))
    a.memory.append(Message(role="assistant", content="A1 from Confucius", phase="opening"))

    a.swap_persona(registry.get("socrates"))
    assert a.persona.id == "socrates"
    # History intact:
    assert len(a.memory.history) == 2
    assert a.memory.history[1].content == "A1 from Confucius"


@pytest.mark.asyncio
async def test_swap_model_does_not_touch_persona_or_history(gateway):
    a = Agent(
        seat=1,
        persona=registry.get("confucius"),
        model=Model(id="deepseek-chat", gateway=gateway),
    )
    a.memory.append(Message(role="user", content="Q", phase="opening"))
    a.swap_model(Model(id="claude-opus-4-7", gateway=gateway))
    assert a.persona.id == "confucius"
    assert a.model.id == "claude-opus-4-7"
    assert len(a.memory.history) == 1


@pytest.mark.asyncio
async def test_swap_log_records_kinds(gateway):
    a = Agent(
        seat=1,
        persona=registry.get("confucius"),
        model=Model(id="deepseek-chat", gateway=gateway),
    )
    a.swap_persona(registry.get("socrates"))
    a.swap_model(Model(id="gpt-4o", gateway=gateway))
    a.swap_persona(registry.get("naval"))
    kinds = [s[0] for s in a.swap_log]
    assert kinds == ["persona", "model", "persona"]


@pytest.mark.asyncio
async def test_speak_routes_to_persona_specific_scripted_reply():
    gw = MockGateway(
        scripted=[
            ScriptedReply(text="REPLY-A", model_id="deepseek-chat", persona_id="confucius"),
            ScriptedReply(text="REPLY-B", model_id="deepseek-chat", persona_id="socrates"),
        ]
    )
    a = Agent(
        seat=1,
        persona=registry.get("confucius"),
        model=Model(id="deepseek-chat", gateway=gw),
    )
    r1 = await a.speak("hi", phase="opening")
    assert r1.text == "REPLY-A"
    a.swap_persona(registry.get("socrates"))
    r2 = await a.speak("again", phase="opening")
    assert r2.text == "REPLY-B"
