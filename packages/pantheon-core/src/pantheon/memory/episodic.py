"""Episodic memory — cross-debate persistent state per (user, persona).

M0: in-memory dict. M1: SQLite. M2: optional Postgres.
"""
from __future__ import annotations

from typing import Protocol


class EpisodicStore(Protocol):
    async def remember(self, key: str, value: dict) -> None: ...
    async def recall(self, key: str) -> dict | None: ...
    async def forget(self, key: str) -> None: ...


class NullEpisodicStore:
    """No-op store. Used in `swap_memory(profile='ephemeral')`."""

    async def remember(self, key: str, value: dict) -> None:
        return

    async def recall(self, key: str) -> dict | None:
        return None

    async def forget(self, key: str) -> None:
        return
