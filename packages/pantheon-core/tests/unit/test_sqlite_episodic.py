"""SqliteEpisodicStore."""
from __future__ import annotations

import pytest
from pantheon.memory.sqlite_episodic import SqliteEpisodicStore


@pytest.fixture
def store(tmp_path):
    return SqliteEpisodicStore(tmp_path / "ep.db")


@pytest.mark.asyncio
async def test_remember_and_recall(store):
    await store.remember("user:wendy:topic:quit_job",
                         {"choice": "stayed", "rationale": "naval persuaded me"})
    out = await store.recall("user:wendy:topic:quit_job")
    assert out == {"choice": "stayed", "rationale": "naval persuaded me"}


@pytest.mark.asyncio
async def test_remember_overwrites(store):
    await store.remember("k", {"v": 1})
    await store.remember("k", {"v": 2})
    out = await store.recall("k")
    assert out == {"v": 2}


@pytest.mark.asyncio
async def test_recall_missing_returns_none(store):
    assert await store.recall("not-there") is None


@pytest.mark.asyncio
async def test_forget(store):
    await store.remember("k", {"v": 1})
    await store.forget("k")
    assert await store.recall("k") is None


@pytest.mark.asyncio
async def test_clear_all_wipes(store):
    await store.remember("a", {"x": 1})
    await store.remember("b", {"y": 2})
    await store.clear_all()
    assert await store.recall("a") is None
    assert await store.recall("b") is None


@pytest.mark.asyncio
async def test_keys_filter_by_prefix(store):
    await store.remember("user:alice:foo", {"x": 1})
    await store.remember("user:bob:bar", {"x": 2})
    await store.remember("session:42:meta", {"x": 3})
    keys = await store.keys("user:")
    assert keys == ["user:alice:foo", "user:bob:bar"]


@pytest.mark.asyncio
async def test_chinese_value_round_trips(store):
    await store.remember("k", {"text": "学而时习之，不亦说乎"})
    out = await store.recall("k")
    assert out["text"] == "学而时习之，不亦说乎"
