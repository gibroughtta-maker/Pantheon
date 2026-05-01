"""Moderator — phase shepherd.

Responsibilities (M0):
  - Compose a per-round summary used by SynthesisPhase
  - Detect "soft consensus" → flag for Devil's Advocate (M1 will spawn one)
  - Decide whether SYNTHESIS should loop again or transition to VERDICT
"""
from __future__ import annotations

from dataclasses import dataclass

from pantheon.core.model import Model
from pantheon.debate.phases import PhaseContext


@dataclass
class Moderator:
    model: Model | None = None  # M0 uses heuristic; M1 will use real LLM summary

    async def summarize(self, ctx: PhaseContext) -> str:
        lines = []
        for seat in sorted(ctx.transcripts):
            speeches = ctx.transcripts[seat]
            last = speeches[-1] if speeches else ""
            lines.append(f"- seat {seat}: {last[:240]}…")
        return "Round summary:\n" + "\n".join(lines)

    def soft_consensus(self, ctx: PhaseContext, threshold: float = 0.85) -> bool:
        """Heuristic: if all last-round speeches share ≥ threshold of common
        word tokens, flag it. Real implementation will use embeddings."""
        last = [v[-1] for v in ctx.transcripts.values() if v]
        if len(last) < 2:
            return False
        toksets = [set(s.lower().split()) for s in last]
        intersection = set.intersection(*toksets) if toksets else set()
        union = set.union(*toksets) if toksets else set()
        if not union:
            return False
        jaccard = len(intersection) / len(union)
        return jaccard >= threshold

    def should_continue_synthesis(self, ctx: PhaseContext, max_rounds: int) -> bool:
        return ctx.rounds_remaining > 0 and ctx.rounds_remaining < max_rounds
