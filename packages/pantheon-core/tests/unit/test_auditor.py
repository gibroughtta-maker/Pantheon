"""Auditor — quote extraction + grounding tagging."""
from __future__ import annotations

import pytest

from pantheon import registry
from pantheon.roles.auditor import Auditor
from pantheon.types.verdict import Claim


@pytest.mark.asyncio
async def test_no_quote_marked_inference():
    a = Auditor()
    c = Claim(claim_id="c1", speaker="confucius#1", text="The journey is long.")
    await a.audit_claim(c, registry.get("confucius"))
    assert c.type == "inference"
    assert c.grounding_tag == "no_corpus"


@pytest.mark.asyncio
async def test_quote_with_no_corpus_marked_unverified():
    a = Auditor()
    c = Claim(
        claim_id="c1",
        speaker="confucius#1",
        text='Confucius said: "Learn ceaselessly and be glad."',
    )
    await a.audit_claim(c, registry.get("confucius"))
    # confucius has no actual corpus configured (yet) → grounding_tag downgraded
    assert c.type == "quote"
    assert c.grounding_tag in {"unverified", "no_corpus"}


@pytest.mark.asyncio
async def test_extract_chinese_quote():
    a = Auditor()
    quotes = a._extract_quotes("先师说「己所不欲，勿施于人」")
    assert any("己所不欲" in q for q in quotes)
