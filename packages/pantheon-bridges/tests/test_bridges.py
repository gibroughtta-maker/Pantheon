"""Bridges scaffolding — Obsidian sink works without network; pipe()
isolates per-sink failures; protocol satisfied by all sinks."""
from __future__ import annotations

import pytest

from pantheon import MockGateway, Pantheon, ScriptedReply
from pantheon_bridges import EventSink, pipe
from pantheon_bridges.discord import DiscordSink
from pantheon_bridges.obsidian import ObsidianSink
from pantheon_bridges.telegram import TelegramSink


def test_obsidian_satisfies_protocol(tmp_path):
    s = ObsidianSink(vault=str(tmp_path), folder="P")
    assert isinstance(s, EventSink)


def test_telegram_satisfies_protocol():
    s = TelegramSink(bot_token="t", chat_id="123")
    assert isinstance(s, EventSink)


def test_discord_satisfies_protocol():
    s = DiscordSink(webhook_url="https://example/x")
    assert isinstance(s, EventSink)


@pytest.mark.asyncio
async def test_pipe_writes_obsidian_file(tmp_path):
    gw = MockGateway()
    p = Pantheon.summon(["confucius", "naval"], gateway=gw)
    sess = p.debate("Should I quit my job?", rounds=3, seed=7)
    sink = ObsidianSink(vault=str(tmp_path), folder="P")
    v = await pipe(sess, sinks=[sink])
    out_dir = tmp_path / "P"
    files = list(out_dir.glob("*.md"))
    assert len(files) == 1
    body = files[0].read_text(encoding="utf-8")
    assert "# Should I quit my job?" in body
    assert v.debate_id in body
    assert "## Verdict" in body


@pytest.mark.asyncio
async def test_pipe_isolates_per_sink_failures(tmp_path):
    """A raising sink should not stop sibling sinks from receiving events."""
    class FailingSink:
        name = "boom"
        seen_events: list = []

        async def handle(self, event):
            raise RuntimeError("synthetic failure")

        async def finalize(self, verdict):
            raise RuntimeError("synthetic finalize failure")

    good = ObsidianSink(vault=str(tmp_path), folder="P")
    bad = FailingSink()

    gw = MockGateway()
    p = Pantheon.summon(["confucius", "socrates"], gateway=gw)
    sess = p.debate("Q?", rounds=3, seed=1)
    v = await pipe(sess, sinks=[good, bad])
    assert v is not None
    out = list((tmp_path / "P").glob("*.md"))
    assert len(out) == 1, "good sink should have written despite the bad one"


def test_obsidian_slug_strips_unsafe(tmp_path):
    """The filename slug should only contain safe chars."""
    from pantheon_bridges.obsidian import _slug
    assert _slug("Should I quit?") == "Should-I-quit"
    assert _slug("我应该辞职吗？") == "我应该辞职吗"
    assert _slug("/path/with/slashes") == "pathwithslashes"
    assert _slug("") == "debate"
