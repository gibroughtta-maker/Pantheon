"""Weight system — softmax over log-weights.

`compute_weights` takes a list of `Agent` objects and a topic vector, returns
a dict[seat] → weight (sums to 1.0). v0.3 plan §5.1.

The four log-additive components:
    a · log(skill_match)
    b · log(model_capability)        — uniform 1.0 in M0; pantheon-bench fills later
    c · log(user_preference)         — set via Pantheon.set_weight
    d · log(corpus_coverage)         — 1.0 in M0 (no corpus); will be retrieval recall in M1
"""
from __future__ import annotations

import math

EPSILON = 1e-6


def _safe_log(x: float) -> float:
    return math.log(max(x, EPSILON))


def _cosine_like(skills: dict[str, float], topic: dict[str, float]) -> float:
    """Bounded similarity between persona skills and topic tags. We don't
    require either side to be unit-norm; we just want a [0, 1] score."""
    if not topic:
        return 0.5
    keys = set(skills) | set(topic)
    num = sum(skills.get(k, 0.0) * topic.get(k, 0.0) for k in keys)
    denom_a = math.sqrt(sum(skills.get(k, 0.0) ** 2 for k in keys))
    denom_b = math.sqrt(sum(topic.get(k, 0.0) ** 2 for k in keys))
    if denom_a == 0 or denom_b == 0:
        return 0.5
    raw = num / (denom_a * denom_b)
    return max(0.0, min(1.0, raw))


def compute_weights(
    agents: list,
    topic_tags: dict[str, float] | None = None,
    *,
    user_prefs: dict[int, float] | None = None,
    coefficients: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 0.5),
) -> dict[int, float]:
    """Softmax-of-logs weighting (plan §5.1).

    score(persona)  = a · log(skill_match)
                    + b · log(model_capability)     ← from models.yaml
                    + c · log(user_preference)
                    + d · log(corpus_coverage)      ← non-Null corpus → 1.0

    weight(persona) = softmax(score)
    """
    # Lazy import to avoid an import cycle: bench → calibration.probes
    # imports DIMENSIONS, weights doesn't strictly need bench at import time.
    from pantheon.bench.registry import capability_for
    from pantheon.memory.corpus import NullCorpusStore

    a, b, c, d = coefficients
    topic = topic_tags or {}
    user_prefs = user_prefs or {}
    scores: dict[int, float] = {}
    for ag in agents:
        skill_match = _cosine_like(ag.persona.spec.skills, topic) if topic else 0.5
        cap = capability_for(ag.model.id)
        if topic:
            # Model capability weighted by the topic — same dim as skill.
            model_cap = _cosine_like(cap.skills, topic) or cap.overall
        else:
            model_cap = cap.overall
        user_pref = user_prefs.get(ag.seat, 1.0)
        corpus_cov = 0.4 if isinstance(ag.persona.corpus, NullCorpusStore) else 1.0
        scores[ag.seat] = (
            a * _safe_log(skill_match)
            + b * _safe_log(model_cap)
            + c * _safe_log(user_pref)
            + d * _safe_log(corpus_cov)
        )
    if not scores:
        return {}
    m = max(scores.values())
    exps = {k: math.exp(v - m) for k, v in scores.items()}
    total = sum(exps.values())
    return {k: v / total for k, v in exps.items()}
