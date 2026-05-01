"""L2 — corpus-coverage scorer.

For each (persona, dimension), run all probe questions for that dimension
against the persona's corpus. Score ∈ [0, 1]:

    L2(persona, dim) = mean over probes of:
        diversity_factor × normalized_top_score(probe)

  * normalized_top_score = best retrieval similarity, clamped to [0, 1]
  * diversity_factor     = unique_sources_hit / unique_sources_available
                           (rewards corpora that speak to a question from
                            multiple angles, not just one repeated chunk)

A persona with NO corpus or a corpus whose top hit is < min_score on every
probe gets L2 = 0 for that dimension. That's a feature: it correctly says
"this corpus does not cover this dimension."
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pantheon.calibration.probes import DIMENSIONS, Probes
from pantheon.memory.corpus import CorpusStore, RetrievalHit
from pantheon.memory.embedded_corpus import EmbeddedCorpusStore


@dataclass
class L2DimResult:
    score: float
    per_probe: list[float]
    sources_hit: list[str]


@dataclass
class L2Result:
    persona_id: str
    by_dimension: dict[str, L2DimResult] = field(default_factory=dict)

    def vector(self) -> dict[str, float]:
        return {d: r.score for d, r in self.by_dimension.items()}


async def score_l2(
    persona_id: str,
    corpus: CorpusStore,
    probes: Probes,
    *,
    top_k: int = 4,
    min_score: float = 0.20,
) -> L2Result:
    out = L2Result(persona_id=persona_id)

    # Total source count (only known for our embedded store).
    total_sources = 0
    if isinstance(corpus, EmbeddedCorpusStore):
        total_sources = len({c.source for c in corpus._chunks})
    fallback_sources_div = max(total_sources, 1)

    for dim in DIMENSIONS:
        per_probe_scores: list[float] = []
        sources_hit: set[str] = set()
        for q in probes.for_dimension(dim):
            hits: list[RetrievalHit] = await corpus.retrieve(q, top_k=top_k)
            if not hits:
                per_probe_scores.append(0.0)
                continue
            top = hits[0].score
            top_clamped = max(0.0, min(1.0, top))
            if top_clamped < min_score:
                per_probe_scores.append(0.0)
                continue
            per_probe_scores.append(top_clamped)
            for h in hits:
                if h.score >= min_score:
                    sources_hit.add(h.source)
        diversity = len(sources_hit) / fallback_sources_div if total_sources else 1.0
        diversity = min(1.0, diversity * 2.0)  # 50%+ unique sources → full diversity
        mean_top = (
            sum(per_probe_scores) / len(per_probe_scores) if per_probe_scores else 0.0
        )
        score = mean_top * (0.5 + 0.5 * diversity)  # diversity has half-weight
        out.by_dimension[dim] = L2DimResult(
            score=round(score, 4),
            per_probe=[round(x, 4) for x in per_probe_scores],
            sources_hit=sorted(sources_hit),
        )
    return out
