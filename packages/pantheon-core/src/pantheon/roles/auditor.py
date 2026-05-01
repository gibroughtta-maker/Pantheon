"""Auditor — citation verification + grounding scoring.

M0: regex-based quote extraction; corpus check is a stub since corpus is null.
Every direct quote is conservatively marked `unverified` when no corpus is
available. M1 swaps in a real BM25 + vector hybrid retrieval check.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from pantheon.core.persona import Persona
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
    async def audit_claim(self, claim: Claim, persona: Persona | None) -> Claim:
        """Tag claim with grounding info. Mutates and returns the claim."""
        text = claim.text
        quotes = self._extract_quotes(text)
        if not quotes:
            claim.type = "inference"
            claim.grounding_score = 0.6
            claim.grounding_tag = "no_corpus"
            return claim
        if persona is None or not persona.spec.corpus.sources:
            # No corpus configured → cannot verify → mark unverified.
            claim.type = "quote"
            claim.grounding_score = 0.3
            claim.grounding_tag = "unverified"
            return claim
        # M1: actually check persona.corpus.has_quote(q) for each q.
        verified = 0
        for q in quotes:
            if await persona.corpus.has_quote(q):
                verified += 1
        if verified == len(quotes):
            claim.grounding_score = 0.9
            claim.grounding_tag = "verified"
        elif verified > 0:
            claim.grounding_score = 0.6
            claim.grounding_tag = "unverified"
        else:
            claim.grounding_score = 0.3
            claim.grounding_tag = "unverified"
        claim.type = "quote"
        return claim

    @staticmethod
    def _extract_quotes(text: str) -> list[str]:
        out: list[str] = []
        for pat in _QUOTE_PATTERNS:
            out.extend(pat.findall(text))
        return [q.strip() for q in out if len(q.strip()) >= 4]
