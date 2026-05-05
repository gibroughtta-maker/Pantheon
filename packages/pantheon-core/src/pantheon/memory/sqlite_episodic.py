"""SQLite-backed episodic memory.

Implements `EpisodicStore` with a single ``episodic`` table:

    CREATE TABLE episodic (
        key       TEXT PRIMARY KEY,
        value     TEXT NOT NULL,    -- JSON
        updated   TEXT NOT NULL     -- ISO 8601
    );

Used to remember things across debates: "the user asked about quitting
their job last month and chose option B" → next debate, the personas can
be primed with that context. Per the v0.3 plan §1.1, episodic memory is
permanent (until explicitly cleared), tied to the user (or process), and
never blocks an LLM call.

By design, all reads/writes are async (the public Protocol is async), but
under the hood we use sqlite3 in a worker thread via ``asyncio.to_thread``
to avoid blocking the event loop.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class SqliteEpisodicStore:
    """SQLite-backed episodic memory. Open with a path, share across debates."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".pantheon" / "episodic.db"
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS episodic (
                       key     TEXT PRIMARY KEY,
                       value   TEXT NOT NULL,
                       updated TEXT NOT NULL
                   )"""
            )
            conn.commit()

    async def remember(self, key: str, value: dict) -> None:
        payload = json.dumps(value, ensure_ascii=False)
        ts = datetime.now(UTC).isoformat()

        def _do() -> None:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO episodic(key, value, updated) VALUES(?,?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated",
                    (key, payload, ts),
                )
                conn.commit()

        async with self._lock:
            await asyncio.to_thread(_do)

    async def recall(self, key: str) -> dict | None:
        def _do() -> dict | None:
            with self._connect() as conn:
                cur = conn.execute("SELECT value FROM episodic WHERE key = ?", (key,))
                row = cur.fetchone()
                return json.loads(row["value"]) if row else None

        return await asyncio.to_thread(_do)

    async def forget(self, key: str) -> None:
        def _do() -> None:
            with self._connect() as conn:
                conn.execute("DELETE FROM episodic WHERE key = ?", (key,))
                conn.commit()

        async with self._lock:
            await asyncio.to_thread(_do)

    async def clear_all(self) -> None:
        """Wipe everything. Used by ``swap_memory(profile='ephemeral')``."""

        def _do() -> None:
            with self._connect() as conn:
                conn.execute("DELETE FROM episodic")
                conn.commit()

        async with self._lock:
            await asyncio.to_thread(_do)

    async def keys(self, prefix: str = "") -> list[str]:
        def _do() -> list[str]:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT key FROM episodic WHERE key LIKE ? ORDER BY key",
                    (f"{prefix}%",),
                )
                return [r["key"] for r in cur.fetchall()]

        return await asyncio.to_thread(_do)
