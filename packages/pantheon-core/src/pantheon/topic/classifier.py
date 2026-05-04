"""Topic classifier — 7-dim vector over (ethics, governance, education,
business, technology, divination, emotion).

Public entry point::

    from pantheon.topic import classify_topic
    tags = classify_topic("Should I quit my job?", user_tags=None,
                          embedder=None, llm_judge=None)
    # → {"business": 0.62, "ethics": 0.18, ...}

Each strategy is independently testable; the runner in `TopicClassifier`
fuses them with the weights from plan §5.2.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

from pantheon.calibration.probes import DIMENSIONS
from pantheon.core.model import Model
from pantheon.memory.embedded_corpus import Embedder, HashEmbedder

# Short anchoring text per dimension, used by the embedding strategy.
DIMENSION_ANCHORS: dict[str, str] = {
    "ethics": (
        "Right and wrong, virtue, duty, fairness, forgiveness, "
        "moral obligation to family / friends / strangers, love thy neighbour."
    ),
    "governance": (
        "Politics, governance, the state, leadership of communities, "
        "the legitimacy of rulers, law and policy, public administration."
    ),
    "education": (
        "Teaching, learning, schools, mentorship, knowledge versus wisdom, "
        "raising children, training the mind, cultivating skill."
    ),
    "business": (
        "Money, work, business, profit, careers, founders, capital, contracts, "
        "co-founders, ownership, salary, jobs, leverage, customers."
    ),
    "technology": (
        "Engineering, machines, code, AI, science, tools, automation, "
        "biotech, the relationship between humans and the systems they build."
    ),
    "divination": (
        "Fortune, signs, omens, the future, fate, intuition versus reason, "
        "dreams, oracles, tradition of consulting the unseen."
    ),
    "emotion": (
        "Grief, love, fear, anger, joy, suffering, comforting others, "
        "facing death, the inner life, mental health and feeling."
    ),
}


def _l2_norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v)) or 1.0


def _cos(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = _l2_norm(a) * _l2_norm(b)
    return max(0.0, min(1.0, sum(x * y for x, y in zip(a, b)) / n))


def _normalize(v: dict[str, float]) -> dict[str, float]:
    """Min-max-then-sum normalize so the largest dim is 1.0 and (typically)
    the smallest is around 0. This is friendlier to the cosine in
    compute_weights than softmax, which compresses everything."""
    if not v:
        return {}
    vmin = min(v.values())
    vmax = max(v.values())
    if vmax == vmin:
        return {k: 0.5 for k in v}
    return {k: (val - vmin) / (vmax - vmin) for k, val in v.items()}


# ============================================================================
# Strategy 2: embedding similarity
# ============================================================================

def classify_topic_embedding(
    question: str,
    embedder: Embedder | None = None,
) -> dict[str, float]:
    """Embed the question + each dimension's anchor; return cosine vector."""
    emb = embedder or HashEmbedder()
    q = emb.embed(question)
    out: dict[str, float] = {}
    for dim in DIMENSIONS:
        a = emb.embed(DIMENSION_ANCHORS[dim])
        out[dim] = _cos(q, a)
    return _normalize(out)


# ============================================================================
# Strategy 3: small-LLM zero-shot
# ============================================================================

_LLM_PROMPT = """\
You are a topic classifier. Given a debate question, score how strongly
each of these 7 dimensions applies. Use a 0.0–1.0 scale where 1.0 means
the question is centrally about that dimension and 0.0 means not at all.

Dimensions: ethics, governance, education, business, technology, divination, emotion.

Output VALID JSON ONLY, no surrounding prose, with EXACTLY this shape:

  {"ethics": 0.0, "governance": 0.0, "education": 0.0, "business": 0.0,
   "technology": 0.0, "divination": 0.0, "emotion": 0.0}

Question: """


async def classify_topic_llm(
    question: str,
    judge: Model,
) -> dict[str, float]:
    """Zero-shot LLM scoring. Falls back to all-zero on parse failure."""
    messages = [{"role": "user", "content": _LLM_PROMPT + question}]
    try:
        result = await judge.call(messages, temperature=0.0, max_tokens=200)
    except Exception:  # noqa: BLE001 — strategy 3 is optional
        return {d: 0.0 for d in DIMENSIONS}
    text = result.text.strip()
    # Extract first {...} block; LLMs sometimes wrap in markdown.
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        return {d: 0.0 for d in DIMENSIONS}
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {d: 0.0 for d in DIMENSIONS}
    out = {d: float(parsed.get(d, 0.0)) for d in DIMENSIONS}
    # Clamp 0..1; unknown dims silently dropped.
    return {k: max(0.0, min(1.0, v)) for k, v in out.items()}


# ============================================================================
# Fusion
# ============================================================================

@dataclass
class TopicClassifier:
    embedder: Embedder | None = None
    llm_judge: Model | None = None
    weights: tuple[float, float, float] = (1.0, 0.6, 0.4)  # tags / embed / llm
    _last_breakdown: dict[str, dict[str, float]] = field(default_factory=dict)

    async def classify(
        self,
        question: str,
        *,
        user_tags: dict[str, float] | None = None,
    ) -> dict[str, float]:
        w_tags, w_emb, w_llm = self.weights

        tags_v: dict[str, float] = {d: 0.0 for d in DIMENSIONS}
        if user_tags:
            for k, v in user_tags.items():
                if k in tags_v:
                    tags_v[k] = float(v)

        emb_v = classify_topic_embedding(question, self.embedder)
        llm_v: dict[str, float] = {d: 0.0 for d in DIMENSIONS}
        if self.llm_judge is not None:
            llm_v = await classify_topic_llm(question, self.llm_judge)

        # Weighted sum, then min-max normalize so the dominant dim is 1.0.
        fused: dict[str, float] = {}
        active_weights = (
            (w_tags if user_tags else 0.0)
            + (w_emb)
            + (w_llm if self.llm_judge is not None else 0.0)
        ) or 1.0
        for d in DIMENSIONS:
            fused[d] = (
                w_tags * tags_v[d]
                + w_emb * emb_v[d]
                + (w_llm * llm_v[d] if self.llm_judge is not None else 0.0)
            ) / active_weights

        self._last_breakdown = {"tags": tags_v, "embedding": emb_v, "llm": llm_v}
        return _normalize(fused)

    def last_breakdown(self) -> dict[str, dict[str, float]]:
        """For audit / debugging: per-strategy scores from the last call."""
        return dict(self._last_breakdown)


async def classify_topic(
    question: str,
    *,
    user_tags: dict[str, float] | None = None,
    embedder: Embedder | None = None,
    llm_judge: Model | None = None,
) -> dict[str, float]:
    """One-shot helper that runs the full fused classifier."""
    cls = TopicClassifier(embedder=embedder, llm_judge=llm_judge)
    return await cls.classify(question, user_tags=user_tags)
