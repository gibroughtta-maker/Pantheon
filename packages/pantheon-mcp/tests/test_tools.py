"""Pantheon MCP tool dispatch."""
from __future__ import annotations

import pytest

from pantheon import MockGateway, ScriptedReply
from pantheon_mcp.sessions import SessionManager
from pantheon_mcp.tools import TOOL_SCHEMAS, handle


@pytest.fixture
def mgr():
    return SessionManager(gateway=MockGateway())


def test_eight_tools_published():
    names = {t["name"] for t in TOOL_SCHEMAS}
    assert names == {
        "summon", "debate", "swap_persona", "swap_model",
        "get_verdict", "cast_divination", "list_personas", "audit_persona",
    }


def test_every_tool_has_input_schema():
    for t in TOOL_SCHEMAS:
        assert "inputSchema" in t
        assert t["inputSchema"]["type"] == "object"


@pytest.mark.asyncio
async def test_summon_returns_session_id(mgr):
    out = await handle("summon", {"personas": ["confucius", "socrates"]}, mgr)
    assert "session_id" in out
    assert len(out["session_id"]) > 8
    assert out["agents"][0]["persona"] == "confucius"
    assert out["agents"][1]["persona"] == "socrates"


@pytest.mark.asyncio
async def test_summon_rejects_too_many(mgr):
    with pytest.raises(ValueError, match="10 seats"):
        await handle("summon", {"personas": ["confucius"] * 11}, mgr)


@pytest.mark.asyncio
async def test_summon_rejects_unknown_persona(mgr):
    with pytest.raises(KeyError):
        await handle("summon", {"personas": ["not-a-real-persona"]}, mgr)


@pytest.mark.asyncio
async def test_list_personas_returns_all_registered(mgr):
    out = await handle("list_personas", {}, mgr)
    ids = {p["id"] for p in out["personas"]}
    assert {"confucius", "socrates", "naval"}.issubset(ids)


@pytest.mark.asyncio
async def test_list_personas_filtered_by_school(mgr):
    out = await handle("list_personas", {"filter": {"school": "儒家"}}, mgr)
    ids = {p["id"] for p in out["personas"]}
    assert "confucius" in ids
    assert "socrates" not in ids


@pytest.mark.asyncio
async def test_audit_persona_returns_metadata(mgr):
    out = await handle("audit_persona", {"persona_id": "confucius"}, mgr)
    assert out["persona_id"] == "confucius"
    assert "audit" in out
    assert "known_biases" in out
    assert isinstance(out["known_biases"], list)


@pytest.mark.asyncio
async def test_cast_divination_placeholder(mgr):
    out = await handle("cast_divination", {"method": "iching", "question": "..."}, mgr)
    assert out["implemented"] is False


@pytest.mark.asyncio
async def test_full_debate_flow(mgr):
    summon = await handle("summon", {"personas": ["confucius", "socrates"]}, mgr)
    sid = summon["session_id"]
    out = await handle("debate", {
        "session_id": sid,
        "question": "Is virtue teachable?",
        "rounds": 3,
        "seed": 42,
    }, mgr)
    assert out["session_id"] == sid
    assert "verdict" in out
    assert out["verdict"]["question"] == "Is virtue teachable?"
    assert len(out["events"]) > 0
    # At least one phase boundary, one speech, one verdict marker.
    types = {e["type"] for e in out["events"]}
    assert {"phase_boundary", "speech", "verdict_marker"}.issubset(types)


@pytest.mark.asyncio
async def test_swap_persona_must_come_after_debate(mgr):
    summon = await handle("summon", {"personas": ["confucius", "socrates"]}, mgr)
    sid = summon["session_id"]
    with pytest.raises(ValueError, match="before swapping"):
        await handle("swap_persona",
                     {"session_id": sid, "seat": 1, "to": "naval"}, mgr)


@pytest.mark.asyncio
async def test_get_verdict_after_debate(mgr):
    summon = await handle("summon", {"personas": ["confucius", "naval"]}, mgr)
    sid = summon["session_id"]
    await handle("debate", {
        "session_id": sid, "question": "Q?", "rounds": 3, "seed": 1
    }, mgr)
    v = await handle("get_verdict", {"session_id": sid}, mgr)
    assert v["question"] == "Q?"
    assert v["debate_id"]


@pytest.mark.asyncio
async def test_unknown_tool_raises(mgr):
    with pytest.raises(ValueError, match="unknown tool"):
        await handle("not_a_tool", {}, mgr)
