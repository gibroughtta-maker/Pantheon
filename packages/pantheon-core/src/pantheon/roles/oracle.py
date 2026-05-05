"""Oracle — final adjudicator.

Computes the verdict from:
  - per-seat speech transcripts
  - per-seat weights (from `compute_weights`)
  - claims + grounding scores from the Auditor
  - relay log + swap warnings

M0: heuristic verdict that surfaces last-round positions, weighted; no LLM
synthesis call. M1 will run an LLM pass for prose consensus paragraphs.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from pantheon.core.agent import Agent
from pantheon.debate.phases import PhaseContext
from pantheon.types.verdict import (
    ActionItem,
    ConsensusPoint,
    CostBreakdown,
    MinorityPoint,
    QualityMetrics,
    RelayLogEntry,
    SpeakerSummary,
    Verdict,
)


@dataclass
class Oracle:
    async def render_verdict(
        self,
        *,
        session_id: str,
        debate_id: str,
        question: str,
        agents: list[Agent],
        weights: dict[int, float],
        ctx: PhaseContext,
        topic_tags: dict[str, float],
        relay_log: list[RelayLogEntry],
        swap_warnings: list[str],
        trace_id: str,
        cost: CostBreakdown,
        duration_ms: int,
        model_calls: int,
        soft_consensus: bool,
        devil_advocate_invoked: bool,
    ) -> Verdict:
        # Per-seat summary
        speaker_summary: list[SpeakerSummary] = []
        avg_grounding_overall = 0.0
        unverified = 0
        for ag in agents:
            speeches = ctx.transcripts.get(ag.seat, [])
            seat_claims = [c for c in ctx.claims if c.speaker.startswith(ag.persona.id)]
            avg_g = (
                sum(c.grounding_score for c in seat_claims) / len(seat_claims)
                if seat_claims
                else 0.0
            )
            avg_grounding_overall += avg_g * weights.get(ag.seat, 0.0)
            unverified += sum(1 for c in seat_claims if c.grounding_tag == "unverified")
            speaker_summary.append(
                SpeakerSummary(
                    seat=ag.seat,
                    persona_id=ag.persona.id,
                    weight=round(weights.get(ag.seat, 0.0), 4),
                    speech_count=len(speeches),
                    avg_grounding=round(avg_g, 3),
                )
            )

        # Heuristic consensus / minority extraction: take each speaker's last
        # speech as their final position, group by token-overlap similarity.
        consensus: list[ConsensusPoint] = []
        minority: list[MinorityPoint] = []
        positions = []
        for ag in agents:
            sps = ctx.transcripts.get(ag.seat, [])
            if not sps:
                continue
            positions.append((ag, sps[-1]))

        if positions:
            # M0 heuristic: top-weighted speaker's final view = primary consensus
            positions.sort(key=lambda p: weights.get(p[0].seat, 0.0), reverse=True)
            top_ag, top_text = positions[0]
            consensus.append(
                ConsensusPoint(
                    statement=_truncate(top_text, 320),
                    supporters=[top_ag.label],
                    weight=round(weights.get(top_ag.seat, 0.0), 4),
                )
            )
            for ag, text in positions[1:]:
                minority.append(
                    MinorityPoint(
                        statement=_truncate(text, 280),
                        holder=ag.label,
                        rationale="Carried into the final round; not resolved by debate.",
                    )
                )

        # Action items: one per top-2 voices (M0 heuristic).
        action_items = [
            ActionItem(
                action=f"Test the position of {ag.label} against your real constraints "
                "for one week before deciding.",
                rationale="Pantheon recommendations are heuristics; ground them in your situation.",
                advocate=ag.label,
            )
            for ag, _ in positions[:2]
        ]

        no_consensus = len(positions) > 1 and weights.get(positions[0][0].seat, 0.0) < 0.4

        if soft_consensus or no_consensus:
            robustness = "low"
        elif len(positions) >= 3:
            robustness = "medium"
        else:
            robustness = "high"

        return Verdict(
            session_id=session_id,
            debate_id=debate_id,
            question=question,
            topic_tags=topic_tags,
            consensus=consensus,
            minority_opinion=minority,
            action_items=action_items,
            speaker_summary=speaker_summary,
            persona_relay_log=relay_log,
            quality=QualityMetrics(
                avg_grounding_score=round(avg_grounding_overall, 3),
                unverified_quote_count=unverified,
                devil_advocate_invoked=devil_advocate_invoked,
                persona_swap_warnings=swap_warnings,
            ),
            no_consensus=no_consensus,
            consensus_robustness=robustness,  # type: ignore[arg-type]
            trace_id=trace_id,
            cost=cost,
            duration_ms=duration_ms,
            model_calls=model_calls,
        )


def _truncate(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


# noqa: keep `time` imported for future use (LLM oracle pass).
_ = time
