"""EmbeddedCorpusStore contracts: chunking, hybrid retrieval, has_quote."""
from __future__ import annotations

import pytest
from pantheon.memory.embedded_corpus import (
    EmbeddedCorpusStore,
    HashEmbedder,
    _chunk_text,
    _cosine,
    _tokenize,
)


def test_chunk_text_paragraphs():
    text = "Para one with some content.\n\nPara two with more.\n\nPara three."
    chunks = _chunk_text(text, max_chars=500)
    assert len(chunks) == 3
    assert chunks[0].startswith("Para one")


def test_chunk_text_long_paragraph_splits():
    long = ("This is a sentence. " * 100).strip()
    chunks = _chunk_text(long, max_chars=120)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 200


def test_tokenize_chinese_chars():
    out = _tokenize("学而时习之 hello world")
    # Each Chinese char is its own token; English words are tokens too.
    assert "学" in out
    assert "时" in out
    assert "hello" in out


def test_cosine_basic():
    assert _cosine([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)
    assert _cosine([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0, abs=1e-6)
    assert _cosine([1, 0, 0], [-1, 0, 0]) == pytest.approx(-1.0)
    assert _cosine([], [1]) == 0.0


def test_hash_embedder_deterministic():
    e = HashEmbedder()
    a = e.embed("hello world")
    b = e.embed("hello world")
    assert a == b
    c = e.embed("goodbye world")
    assert a != c


def test_hash_embedder_normalized():
    e = HashEmbedder()
    v = e.embed("anything at all")
    norm_sq = sum(x * x for x in v)
    assert abs(norm_sq - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_embedded_corpus_retrieval():
    store = EmbeddedCorpusStore(persona_id="test", embedder=HashEmbedder())
    store.add_text(
        "Ethics is about how one should live.\n\n"
        "Governance asks who should rule.\n\n"
        "Education is leading the soul to truth.",
        source="lectures.txt",
    )
    hits = await store.retrieve("How should we live?", top_k=2)
    assert len(hits) == 2
    # Top hit should be ethics-flavoured (best lexical overlap).
    assert "live" in hits[0].text.lower() or "ethics" in hits[0].text.lower()


@pytest.mark.asyncio
async def test_has_quote_substring_match():
    store = EmbeddedCorpusStore(persona_id="test", embedder=HashEmbedder())
    store.add_text("学而时习之，不亦说乎", source="lunyu.txt")
    assert await store.has_quote("学而时习之")
    assert not await store.has_quote("天行健，君子以自强不息")


@pytest.mark.asyncio
async def test_empty_corpus_returns_empty():
    store = EmbeddedCorpusStore(persona_id="test", embedder=HashEmbedder())
    hits = await store.retrieve("any question?", top_k=4)
    assert hits == []
    assert not await store.has_quote("anything")
