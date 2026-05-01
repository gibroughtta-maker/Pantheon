"""L4 — pairwise LLM-judge scorer with Bradley-Terry aggregation.

For each dimension, the target persona is paired against every anchor.
Three judges (configurable LLMs) each cast a vote per pair: A wins, B wins,
or tie. Votes are turned into Bradley-Terry strength estimates, then
re-anchored to the [0,1] interval defined by the anchors' known scores.

Mathematically:
    Each persona p has latent strength θ_p.
    P(p beats q) = θ_p / (θ_p + θ_q).
    Given win counts w_pq we MLE θ via the Zermelo iteration:
        θ_p ← W_p / Σ_q (n_pq / (θ_p + θ_q))

Then we map θ → [0,1] by anchoring two endpoints (highest- and lowest-scored
anchor on this dimension). New persona's score is interpolated.

Ties count as 0.5 win to each side.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal

from pantheon.calibration.probes import DIMENSIONS, Probes
from pantheon.core.model import Model

JudgeVote = Literal["A", "B", "tie"]


@dataclass
class PairwiseRecord:
    target: str
    anchor: str
    dimension: str
    probe: str
    judge_id: str
    vote: JudgeVote
    rationale: str = ""


@dataclass
class L4DimResult:
    score: float
    n_comparisons: int
    win_rate_vs_anchors: dict[str, float]


@dataclass
class L4Result:
    persona_id: str
    by_dimension: dict[str, L4DimResult] = field(default_factory=dict)
    raw_records: list[PairwiseRecord] = field(default_factory=list)

    def vector(self) -> dict[str, float]:
        return {d: r.score for d, r in self.by_dimension.items()}


# ============================================================================
# Bradley-Terry MLE
# ============================================================================

def _bradley_terry(
    win_counts: dict[tuple[str, str], float],
    persona_ids: list[str],
    max_iter: int = 200,
    tol: float = 1e-7,
) -> dict[str, float]:
    """Zermelo's iterative MLE for Bradley-Terry. Returns θ for each persona,
    arbitrarily normalized so they sum to len(personas)."""
    if not persona_ids:
        return {}
    theta = {p: 1.0 for p in persona_ids}
    # totals: W_p (wins), n_pq (matches between p,q)
    W: dict[str, float] = {p: 0.0 for p in persona_ids}
    matches: dict[tuple[str, str], float] = {}
    for (p, q), w in win_counts.items():
        W[p] = W.get(p, 0.0) + w
        key = tuple(sorted((p, q)))
        matches[key] = matches.get(key, 0.0) + w
    # n_pq = sum of both directions
    pair_n: dict[tuple[str, str], float] = {}
    for (p, q), w in win_counts.items():
        key = tuple(sorted((p, q)))
        pair_n[key] = pair_n.get(key, 0.0) + w
    for _ in range(max_iter):
        prev = dict(theta)
        new_theta = {}
        for p in persona_ids:
            denom = 0.0
            for q in persona_ids:
                if q == p:
                    continue
                key = tuple(sorted((p, q)))
                n = pair_n.get(key, 0.0)
                if n == 0:
                    continue
                denom += n / (theta[p] + theta[q])
            if denom <= 0:
                new_theta[p] = theta[p]
            else:
                new_theta[p] = max(W.get(p, 0.0), 1e-9) / denom
        # normalize so sum = len(persona_ids) for stability
        s = sum(new_theta.values()) or 1.0
        scale = len(persona_ids) / s
        new_theta = {k: v * scale for k, v in new_theta.items()}
        diff = sum(abs(new_theta[k] - prev[k]) for k in new_theta)
        theta = new_theta
        if diff < tol:
            break
    return theta


def _anchor_to_unit(
    theta: dict[str, float],
    anchor_scores: dict[str, float],
) -> dict[str, float]:
    """Linearly map θ-space onto the [min, max] of anchor known scores so the
    target persona gets a comparable [0,1] number. If only 1 anchor known
    score is available, fall back to a sigmoid around it."""
    known = {p: s for p, s in anchor_scores.items() if p in theta}
    if not known:
        # No grounding → just normalize θ to [0,1] by min-max.
        vmin, vmax = min(theta.values()), max(theta.values())
        if vmax == vmin:
            return {p: 0.5 for p in theta}
        return {p: (v - vmin) / (vmax - vmin) for p, v in theta.items()}
    if len(known) == 1:
        anchor_p, anchor_s = next(iter(known.items()))
        anchor_theta = theta[anchor_p]
        return {
            p: max(0.0, min(1.0, anchor_s + 0.25 * (theta[p] - anchor_theta)))
            for p in theta
        }
    # 2+ anchors → linear regression θ → score.
    xs = [theta[p] for p in known]
    ys = [known[p] for p in known]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den else 0.0
    intercept = mean_y - slope * mean_x
    return {p: max(0.0, min(1.0, slope * theta[p] + intercept)) for p in theta}


# ============================================================================
# Judge prompting
# ============================================================================

_JUDGE_TEMPLATE = """You are a calibrator for a multi-agent debate system.
Two personas are competing on a single skill dimension. Your job is to pick
which is stronger ON THIS DIMENSION based on the corpus excerpts shown.

Skill dimension: {dimension}
Test question:   {probe}

PERSONA A: {a_id}
A's strongest corpus excerpt for this question:
\"\"\"
{a_excerpt}
\"\"\"

PERSONA B: {b_id}
B's strongest corpus excerpt for this question:
\"\"\"
{b_excerpt}
\"\"\"

Respond with EXACTLY one line: "VOTE: A" or "VOTE: B" or "VOTE: TIE",
followed by a one-sentence rationale on the next line.
"""


def _parse_vote(text: str) -> tuple[JudgeVote, str]:
    text = text.strip()
    first = text.splitlines()[0].upper() if text else ""
    rationale = "\n".join(text.splitlines()[1:]).strip()
    if "VOTE: A" in first or first.endswith("A"):
        return "A", rationale
    if "VOTE: B" in first or first.endswith("B"):
        return "B", rationale
    return "tie", rationale


# ============================================================================
# Public scorer
# ============================================================================

async def score_l4(
    target_persona,
    anchor_personas: list,
    probes: Probes,
    judges: list[Model],
    *,
    seed: int | None = None,
) -> L4Result:
    """Run pairwise tournament for `target_persona` vs each `anchor_personas`
    across all DIMENSIONS × probes × judges. Apply Bradley-Terry to the
    aggregated wins. Return per-dimension scores anchored to the anchors'
    known skill values.
    """
    out = L4Result(persona_id=target_persona.id)
    persona_ids = [target_persona.id] + [a.id for a in anchor_personas]
    persona_lookup = {target_persona.id: target_persona}
    for a in anchor_personas:
        persona_lookup[a.id] = a

    for dim in DIMENSIONS:
        win_counts: dict[tuple[str, str], float] = {}
        for q in probes.for_dimension(dim):
            target_excerpt = await _excerpt_for(target_persona, q)
            for anchor in anchor_personas:
                anchor_excerpt = await _excerpt_for(anchor, q)
                pairwise_messages = [
                    {
                        "role": "user",
                        "content": _JUDGE_TEMPLATE.format(
                            dimension=dim,
                            probe=q,
                            a_id=target_persona.id,
                            a_excerpt=target_excerpt,
                            b_id=anchor.id,
                            b_excerpt=anchor_excerpt,
                        ),
                    }
                ]
                judge_results = await asyncio.gather(
                    *[
                        j.call(pairwise_messages, temperature=0.0, seed=seed, max_tokens=200)
                        for j in judges
                    ]
                )
                for j, jr in zip(judges, judge_results):
                    vote, rationale = _parse_vote(jr.text)
                    out.raw_records.append(
                        PairwiseRecord(
                            target=target_persona.id,
                            anchor=anchor.id,
                            dimension=dim,
                            probe=q,
                            judge_id=j.id,
                            vote=vote,
                            rationale=rationale[:300],
                        )
                    )
                    if vote == "A":
                        win_counts[(target_persona.id, anchor.id)] = (
                            win_counts.get((target_persona.id, anchor.id), 0.0) + 1.0
                        )
                    elif vote == "B":
                        win_counts[(anchor.id, target_persona.id)] = (
                            win_counts.get((anchor.id, target_persona.id), 0.0) + 1.0
                        )
                    else:
                        win_counts[(target_persona.id, anchor.id)] = (
                            win_counts.get((target_persona.id, anchor.id), 0.0) + 0.5
                        )
                        win_counts[(anchor.id, target_persona.id)] = (
                            win_counts.get((anchor.id, target_persona.id), 0.0) + 0.5
                        )

        if not win_counts:
            out.by_dimension[dim] = L4DimResult(
                score=0.5, n_comparisons=0, win_rate_vs_anchors={}
            )
            continue

        theta = _bradley_terry(win_counts, persona_ids)
        anchor_scores = {a.id: a.spec.skills.get(dim, 0.5) for a in anchor_personas}
        unit = _anchor_to_unit(theta, anchor_scores)
        target_score = unit.get(target_persona.id, 0.5)

        n = sum(win_counts.values())
        win_rates = {}
        for anchor in anchor_personas:
            wins = win_counts.get((target_persona.id, anchor.id), 0.0)
            losses = win_counts.get((anchor.id, target_persona.id), 0.0)
            tot = wins + losses
            win_rates[anchor.id] = round(wins / tot, 3) if tot else 0.5
        out.by_dimension[dim] = L4DimResult(
            score=round(target_score, 4),
            n_comparisons=int(n),
            win_rate_vs_anchors=win_rates,
        )
    return out


async def _excerpt_for(persona, query: str) -> str:
    """Pull the persona's best corpus excerpt for the query. If the persona
    has no corpus the persona's display + system prompt summary are used."""
    hits = await persona.corpus.retrieve(query, top_k=1)
    if hits:
        return f"[{hits[0].source}] {hits[0].text[:400]}"
    return f"(no corpus available for {persona.id}; system prompt: {persona.spec.system_prompt[:200]})"
