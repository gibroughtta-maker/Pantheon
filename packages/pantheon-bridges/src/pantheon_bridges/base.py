"""EventSink protocol + pipe() helper."""
from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable

from pantheon.debate.session import Session
from pantheon.types.verdict import Verdict


@runtime_checkable
class EventSink(Protocol):
    """A consumer of Pantheon debate events.

    Implementations should be async-safe and tolerant of failure: a
    raising sink should not bring down sibling sinks. ``pipe()``
    isolates failures per-sink.
    """

    name: str

    async def handle(self, event) -> None: ...
    async def finalize(self, verdict: Verdict) -> None: ...


async def pipe(session: Session, *, sinks: list[EventSink]) -> Verdict:
    """Consume ``session.stream()`` once, forwarding each event to all
    sinks. Returns the final verdict.

    Failures in any one sink are caught and logged — they do not
    interrupt the debate or starve sibling sinks.
    """
    import logging

    log = logging.getLogger("pantheon-bridges.pipe")
    async for ev in session.stream():
        await asyncio.gather(
            *[_safe_handle(s, ev, log) for s in sinks],
            return_exceptions=True,
        )
    verdict = await session.verdict()
    await asyncio.gather(
        *[_safe_finalize(s, verdict, log) for s in sinks],
        return_exceptions=True,
    )
    return verdict


async def _safe_handle(sink: EventSink, event, log) -> None:
    try:
        await sink.handle(event)
    except Exception as e:  # noqa: BLE001
        log.warning("sink %s.handle failed: %s", getattr(sink, "name", sink), e)


async def _safe_finalize(sink: EventSink, verdict: Verdict, log) -> None:
    try:
        await sink.finalize(verdict)
    except Exception as e:  # noqa: BLE001
        log.warning("sink %s.finalize failed: %s", getattr(sink, "name", sink), e)
