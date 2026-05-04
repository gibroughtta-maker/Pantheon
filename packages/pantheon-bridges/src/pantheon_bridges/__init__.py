"""Bridges from Pantheon debate events to external destinations.

Public API:

    from pantheon_bridges import EventSink, pipe
    from pantheon_bridges.obsidian import ObsidianSink
    from pantheon_bridges.telegram import TelegramSink
    from pantheon_bridges.discord  import DiscordSink

    await pipe(session, sinks=[ObsidianSink(...), TelegramSink(...)])

Each `EventSink` implements `handle(event)` async; `pipe()` consumes
`session.stream()` once and forwards each event to every sink in turn.
On verdict, sinks are given a chance to flush via `finalize(verdict)`.
"""
from pantheon_bridges.base import EventSink, pipe

__all__ = ["EventSink", "pipe"]
__version__ = "0.1.0a0"
