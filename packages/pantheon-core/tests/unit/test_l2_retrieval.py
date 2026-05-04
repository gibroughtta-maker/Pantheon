"""L2 retrieval scorer."""
from __future__ import annotations

import pytest

from pantheon.calibration.l2_retrieval import score_l2
from pantheon.calibration.probes import DIMENSIONS, load_probes
from pantheon.memory.corpus import NullCorpusStore
from pantheon.memory.embedded_corpus import EmbeddedCorpusStore, HashEmbedder


@pytest.mark.asyncio
async def test_l2_zero_for_null_corpus():
    probes = load_probes()
    res = await score_l2("nobody", NullCorpusStore("nobody"), probes)
    assert set(res.by_dimension.keys()) == set(DIMENSIONS)
    for dim in DIMENSIONS:
        assert res.by_dimension[dim].score == 0.0


@pytest.mark.asyncio
async def test_l2_nonzero_when_corpus_matches():
    probes = load_probes()
    store = EmbeddedCorpusStore(persona_id="x", embedder=HashEmbedder())
    # Stuff the corpus with a paragraph that lexically overlaps the ethics probes
    store.add_text(
        "When a friend wrongs you, forgiveness restores the bond.\n\n"
        "Wealth is not incompatible with virtue if pursued by the right means.\n\n"
        "Anger may be righteous when defending the powerless.\n\n"
        "Forgive your enemies: it is the harder, higher path.",
        source="ethics.txt",
    )
    res = await score_l2("x", store, probes)
    # Ethics dim should score > 0; others without corpus support stay near 0.
    assert res.by_dimension["ethics"].score > 0.0
    assert res.by_dimension["ethics"].score >= res.by_dimension["technology"].score


@pytest.mark.asyncio
async def test_l2_vector_shape():
    probes = load_probes()
    res = await score_l2("x", NullCorpusStore("x"), probes)
    v = res.vector()
    assert set(v.keys()) == set(DIMENSIONS)
    for s in v.values():
        assert 0.0 <= s <= 1.0
