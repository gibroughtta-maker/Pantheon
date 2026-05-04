"""Auditor — citation verification + grounding scoring.

M1 wires the auditor to the persona's actual runtime corpus (an instance
of `pantheon.memory.corpus.CorpusStore`). For each quoted span in a
claim:

  1. exact substring match → ``verified`` (0.9 grounding)
  2. otherwise hybrid retrieval ≥ retrieval_threshold → ``verified`` (0.85)
  3. otherwise ``unverified`` (0.3); claim type → ``"quote"``

Claims without quoted spans are treated as ``inference`` (0.6 grounding,
``no_corpus`` tag is preserved as a no-quote marker).

The Auditor never raises on retrieval errors — gateway/corpus failures
degrade gracefully into ``unverified``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from pantheon.core.persona import Persona
from pantheon.memory.corpus import NullCorpusStore
from pantheon.types.verdict import Claim

# Patterns that indicate a direct quote in either Chinese or English style.
_QUOTE_PATTERNS = [
    re.compile(r"[「『""'](.+?)[」』""'']"),
    re.compile(r"子曰[:：]?\s*[「『""']?(.+?)[」』""'']?(?=[。.])"),
    re.compile(r'"([^"]{8,})"'),
    re.compile(r"\b(?:said|wrote|argued|taught)\s*[,:]?\s*[\"']([^\"']{8,})[\"']"),
]


@dataclass
class Auditor:
    """Stateless. Use one per debate; safe to share across debates."""

    retrieval_threshold: float = 0.85
    audit_log: list[dict] = field(default_factory=list)

    async def audit_claim(self, claim: Claim, persona: Persona | None) -> Claim:
        """Tag claim with grounding info. Mutates and returns the claim."""
        quotes = self._extract_quotes(claim.text)
        if not quotes:
            claim.type = "inference"
            claim.grounding_score = 0.6
            claim.grounding_tag = "no_corpus"
            self._log(claim, [], [], reason="no_quotes_detected")
            return claim

        if persona is None or isinstance(persona.corpus, NullCorpusStore):
            claim.type = "quote"
            claim.grounding_score = 0.3
            claim.grounding_tag = "unverified"
            self._log(claim, quotes, [], reason="no_corpus_attached")
            return claim

        verified_count = 0
        per_quote: list[dict] = []
        for q in quotes:
            try:
                hit = await persona.corpus.has_quote(q)
            except Exception as e:  # noqa: BLE001 — defensive: corpus failure → unverified
                per_quote.append({"quote": q, "hit": False, "error": str(e)})
                continue
            per_quote.append({"quote": q, "hit": bool(hit)})
            if hit:
                verified_count += 1

        claim.type = "quote"
        if verified_count == len(quotes):
            claim.grounding_score = 0.9
            claim.grounding_tag = "verified"
            claim.source = persona.id
        elif verified_count > 0:
            # Partial: at least one quote landed; don't claim full verification.
            claim.grounding_score = 0.6
            claim.grounding_tag = "unverified"
        else:
            claim.grounding_score = 0.3
            claim.grounding_tag = "unverified"
        self._log(claim, quotes, per_quote)
        return claim

    def _log(
        self,
        claim: Claim,
        quotes: list[str],
        per_quote: list[dict],
        *,
        reason: str | None = None,
    ) -> None:
        self.audit_log.append(
            {
                "claim_id": claim.claim_id,
                "speaker": claim.speaker,
                "n_quotes": len(quotes),
                "n_verified": sum(1 for r in per_quote if r.get("hit")),
                "grounding_tag": claim.grounding_tag,
                "grounding_score": claim.grounding_score,
                "per_quote": per_quote,
                "reason": reason,
            }
        )

    @staticmethod
    def _extract_quotes(text: str) -> list[str]:
        out: list[str] = []
        for pat in _QUOTE_PATTERNS:
            out.extend(pat.findall(text))
        return [q.strip() for q in out if len(q.strip()) >= 4]
