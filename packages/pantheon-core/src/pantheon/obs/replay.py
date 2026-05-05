"""Replay recorder.

For each debate we write a JSONL file at `~/.pantheon/sessions/<debate_id>.jsonl`
(or wherever the user configured). Every LLM call is logged as
``{"event": "llm_call", ...}``; every event emitted by the FSM is logged as
``{"event": "debate_event", ...}``.

`pantheon replay <debate_id>` constructs a `ReplayGateway` from this file and
re-runs the debate deterministically.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from pantheon.gateway.base import CallResult


def debate_id_for(question: str, agents_signature: str, seed: int | None) -> str:
    h = hashlib.sha256()
    h.update(question.encode())
    h.update(b"\x00")
    h.update(agents_signature.encode())
    h.update(b"\x00")
    h.update(str(seed).encode() if seed is not None else b"<random>")
    return h.hexdigest()[:16]


def default_session_dir() -> Path:
    return Path(os.environ.get("PANTHEON_SESSIONS_DIR", str(Path.home() / ".pantheon" / "sessions")))


def _to_jsonable(obj):
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj


class Recorder:
    """Append-only JSONL writer. Open at debate start, close at end."""

    def __init__(self, path: str | Path | None = None, *, debate_id: str | None = None):
        if path is None:
            d = default_session_dir()
            d.mkdir(parents=True, exist_ok=True)
            assert debate_id is not None
            self._path = d / f"{debate_id}.jsonl"
        else:
            self._path = Path(path)
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = None
        self._open()

    def _open(self) -> None:
        self._fh = self._path.open("a", encoding="utf-8")

    @property
    def path(self) -> Path:
        return self._path

    def write(self, event: str, **fields) -> None:
        if self._fh is None:
            self._open()
        row = {
            "event": event,
            "ts": datetime.now(UTC).isoformat(),
            **_to_jsonable(fields),
        }
        self._fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._fh.flush()

    def record_llm_call(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        result: CallResult,
    ) -> None:
        self.write(
            "llm_call",
            model_id=model_id,
            messages=messages,
            text=result.text,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
        )

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def __enter__(self) -> Recorder:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
