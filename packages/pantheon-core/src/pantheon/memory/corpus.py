"""Corpus store — per-persona retrievable text used for RAG-grounded speech.

M0: NullCorpusStore (no-op). M1 will add a real sqlite-vec backend.
The interface is fixed so debate code never needs to special-case "no corpus".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class RetrievalHit:
    text: str
    source: str          # path or canonical citation key
    score: float
    offset: int = 0


class CorpusStore(Protocol):
    """Protocol so multiple backends (null, sqlite-vec, pgvector) interop."""

    persona_id: str

    async def retrieve(self, query: str, top_k: int = 4) -> list[RetrievalHit]: ...
    async def has_quote(self, quote: str) -> bool: ...


class NullCorpusStore:
    """No-op corpus. Used when a persona has no `corpus.sources` configured."""

    def __init__(self, persona_id: str) -> None:
        self.persona_id = persona_id

    async def retrieve(self, query: str, top_k: int = 4) -> list[RetrievalHit]:
        return []

    async def has_quote(self, quote: str) -> bool:
        return False
