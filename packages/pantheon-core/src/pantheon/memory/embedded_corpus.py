"""In-memory corpus store with pluggable embeddings.

Implements `pantheon.memory.corpus.CorpusStore` Protocol. Two embedders ship:

  * ``HashEmbedder``       — deterministic, dependency-free, used by tests.
  * ``SentenceTransformerEmbedder`` — real semantic embeddings; requires the
    ``calibration`` extra (``pip install pantheon-debate[calibration]``).

The store also computes a BM25-style lexical score in parallel with the
embedding similarity so verbatim quotes still hit even if the embedder
is the hash stub. The two are combined with a weight.

Persistence to sqlite-vec is deferred to M2; for now corpora are loaded into
memory at startup. Built-in personas have small enough corpora (< 5 MB total)
that this is fine.
"""
from __future__ import annotations

import hashlib
import math
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import yaml

from pantheon.memory.corpus import RetrievalHit

# ============================================================================
# Embedder Protocol + implementations
# ============================================================================

class Embedder(Protocol):
    dim: int
    name: str

    def embed(self, text: str) -> list[float]: ...


@dataclass
class HashEmbedder:
    """Deterministic, dep-free embedder. Hash text into a fixed-dim vector
    via SHA-256 + L2 normalize. Useless for semantics but perfect for tests:
    same input → same output, no network, no model download.

    Resolution is poor: only character-bigram overlap survives. Combine with
    BM25 for any real lexical signal.
    """

    dim: int = 64
    name: str = "hash-stub"

    def embed(self, text: str) -> list[float]:
        text = text.lower().strip()
        # char-bigram bag → hashed projection
        bigrams = [text[i : i + 2] for i in range(max(0, len(text) - 1))] or [text]
        vec = [0.0] * self.dim
        for bg in bigrams:
            h = hashlib.sha256(bg.encode("utf-8")).digest()
            for i in range(self.dim):
                # signed contribution from byte i (or wraparound)
                b = h[i % len(h)]
                vec[i] += (b - 128) / 128.0
        # L2 normalize
        n = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / n for x in vec]


class SentenceTransformerEmbedder:
    """Lazy-loaded semantic embedder. Requires the ``calibration`` extra."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError(
                "SentenceTransformerEmbedder requires the 'calibration' extra. "
                "Install with `pip install pantheon-debate[calibration]`."
            ) from e
        self._model = SentenceTransformer(model_name)
        self.name = model_name
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, text: str) -> list[float]:
        v = self._model.encode(text, normalize_embeddings=True)
        return [float(x) for x in v.tolist()]


def default_embedder() -> Embedder:
    """Pick the best embedder available. Falls back to HashEmbedder if
    sentence-transformers isn't installed."""
    try:
        return SentenceTransformerEmbedder()
    except ImportError:
        return HashEmbedder()


# ============================================================================
# In-memory corpus store
# ============================================================================

_PARAGRAPH_RE = re.compile(r"\n\s*\n")
_SENTENCE_RE = re.compile(r"(?<=[。！？!?])\s|(?<=[.!?])\s+(?=[A-Z])")


def _chunk_text(text: str, max_chars: int = 480) -> list[str]:
    """Split corpus text into retrieval chunks. Paragraphs first; sentences
    if a paragraph is too long; hard-cut as last resort."""
    chunks: list[str] = []
    for para in _PARAGRAPH_RE.split(text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_chars:
            chunks.append(para)
            continue
        # too long → split by sentence
        buf = ""
        for sent in _SENTENCE_RE.split(para):
            sent = sent.strip()
            if not sent:
                continue
            if len(buf) + len(sent) + 1 <= max_chars:
                buf = (buf + " " + sent).strip()
            else:
                if buf:
                    chunks.append(buf)
                if len(sent) > max_chars:
                    # hard cut
                    for i in range(0, len(sent), max_chars):
                        chunks.append(sent[i : i + max_chars])
                    buf = ""
                else:
                    buf = sent
        if buf:
            chunks.append(buf)
    return chunks


def _tokenize(text: str) -> list[str]:
    """Simple multilingual tokenizer: split CJK char-by-char, others on word boundaries."""
    out: list[str] = []
    for m in re.finditer(r"[一-鿿]|[a-zA-Z][a-zA-Z']*|\d+", text.lower()):
        out.append(m.group(0))
    return out


def _bm25_score(query_tokens: list[str], doc_tokens: list[str], idf: dict[str, float],
                avgdl: float, k1: float = 1.5, b: float = 0.75) -> float:
    if not doc_tokens:
        return 0.0
    score = 0.0
    dl = len(doc_tokens)
    tf: dict[str, int] = {}
    for t in doc_tokens:
        tf[t] = tf.get(t, 0) + 1
    for q in query_tokens:
        if q not in idf:
            continue
        f = tf.get(q, 0)
        if f == 0:
            continue
        score += idf[q] * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / max(avgdl, 1.0)))
    return score


@dataclass
class _Chunk:
    text: str
    source: str
    offset: int
    embedding: list[float]
    tokens: list[str]


@dataclass
class EmbeddedCorpusStore:
    """In-memory corpus with hybrid (embedding + BM25) retrieval."""

    persona_id: str
    embedder: Embedder = field(default_factory=default_embedder)
    embedding_weight: float = 0.6  # vs BM25
    _chunks: list[_Chunk] = field(default_factory=list)
    _idf: dict[str, float] = field(default_factory=dict)
    _avgdl: float = 0.0

    def add_text(self, text: str, *, source: str) -> int:
        """Add a corpus document. Returns number of chunks created."""
        offset = 0
        added = 0
        for chunk in _chunk_text(text):
            tokens = _tokenize(chunk)
            self._chunks.append(
                _Chunk(
                    text=chunk,
                    source=source,
                    offset=offset,
                    embedding=self.embedder.embed(chunk),
                    tokens=tokens,
                )
            )
            offset += len(chunk) + 2
            added += 1
        self._reindex()
        return added

    def _reindex(self) -> None:
        n = len(self._chunks) or 1
        df: dict[str, int] = {}
        total_len = 0
        for c in self._chunks:
            total_len += len(c.tokens)
            for t in set(c.tokens):
                df[t] = df.get(t, 0) + 1
        self._avgdl = total_len / n
        self._idf = {
            t: math.log((n - dft + 0.5) / (dft + 0.5) + 1.0) for t, dft in df.items()
        }

    def __len__(self) -> int:
        return len(self._chunks)

    async def retrieve(self, query: str, top_k: int = 4) -> list[RetrievalHit]:
        if not self._chunks:
            return []
        qvec = self.embedder.embed(query)
        qtoks = _tokenize(query)
        # bm25 max for normalization
        bm_scores = [
            _bm25_score(qtoks, c.tokens, self._idf, self._avgdl) for c in self._chunks
        ]
        bm_max = max(bm_scores) or 1.0
        scored: list[tuple[float, _Chunk]] = []
        for chunk, bm in zip(self._chunks, bm_scores):
            cos = _cosine(qvec, chunk.embedding)
            score = self.embedding_weight * cos + (1 - self.embedding_weight) * (bm / bm_max)
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for sc, ch in scored[:top_k]:
            out.append(
                RetrievalHit(text=ch.text, source=ch.source, score=float(sc), offset=ch.offset)
            )
        return out

    async def has_quote(self, quote: str) -> bool:
        """Verbatim or near-verbatim membership check. Used by Auditor."""
        q = quote.strip().lower()
        if not q:
            return False
        # Exact substring check first (cheap)
        for c in self._chunks:
            if q in c.text.lower():
                return True
        # Fall back to retrieval threshold for near-match.
        hits = await self.retrieve(quote, top_k=1)
        return bool(hits and hits[0].score >= 0.85)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


# ============================================================================
# Loader: build a store from a persona corpus directory
# ============================================================================

def load_corpus_for_persona(
    persona_id: str,
    corpus_dir: str | Path,
    embedder: Embedder | None = None,
) -> EmbeddedCorpusStore:
    """Walk ``corpus_dir``, ingest .txt files, return populated store.

    If ``corpus_dir/manifest.yaml`` exists, only the files listed in it are
    ingested — this lets a persona ship a corpus dir with extras (notes,
    comparisons) without contaminating retrieval.
    """
    corpus_dir = Path(corpus_dir)
    store = EmbeddedCorpusStore(persona_id=persona_id, embedder=embedder or default_embedder())
    files: list[tuple[Path, str]] = []
    manifest_path = corpus_dir / "manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        for entry in manifest.get("sources", []):
            relpath = entry.get("path") or entry.get("file")
            if not relpath:
                continue
            full = corpus_dir / relpath
            if full.exists():
                files.append((full, str(entry.get("source", relpath))))
    else:
        for txt in sorted(corpus_dir.rglob("*.txt")):
            files.append((txt, str(txt.relative_to(corpus_dir))))
    for path, source in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        store.add_text(text, source=source)
    return store


# Required by RetrievalHit's struct construction (kept here so import order
# doesn't matter for tests that only import this module).
_ = struct
