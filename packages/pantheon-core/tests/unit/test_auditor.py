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


@pytest.mark.asyncio
async def test_quote_from_real_corpus_is_verified():
    """A quote that is verbatim in the persona's corpus should get
    grounding_tag='verified'."""
    a = Auditor()
    confucius = registry.get("confucius")
    # Confucius corpus contains 「己所不欲，勿施于人」 — direct match.
    c = Claim(
        claim_id="c1",
        speaker="confucius#1",
        text="The master said「己所不欲，勿施于人」.",
    )
    await a.audit_claim(c, confucius)
    assert c.grounding_tag == "verified", (
        f"expected verified; got {c.grounding_tag} (audit log: {a.audit_log})"
    )
    assert c.grounding_score >= 0.85
    assert c.source == "confucius"


@pytest.mark.asyncio
async def test_fabricated_quote_marked_unverified_against_real_corpus():
    a = Auditor()
    confucius = registry.get("confucius")
    c = Claim(
        claim_id="c1",
        speaker="confucius#1",
        # An invented Confucius quote — should NOT match Lunyu.
        text="The master said「机器人是国家未来之本也」.",
    )
    await a.audit_claim(c, confucius)
    assert c.grounding_tag == "unverified"
    assert c.grounding_score <= 0.5


@pytest.mark.asyncio
async def test_audit_log_records_each_claim():
    a = Auditor()
    confucius = registry.get("confucius")
    c1 = Claim(claim_id="c1", speaker="confucius#1",
               text="子曰「学而时习之，不亦说乎」.")
    c2 = Claim(claim_id="c2", speaker="confucius#1",
               text="A general remark with no quotation here.")
    await a.audit_claim(c1, confucius)
    await a.audit_claim(c2, confucius)
    assert len(a.audit_log) == 2
    # First entry has at least one quote; second has none.
    assert a.audit_log[0]["n_quotes"] >= 1
    assert a.audit_log[1]["n_quotes"] == 0
