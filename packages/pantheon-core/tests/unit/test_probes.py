"""Probes loader contracts."""
from __future__ import annotations

import pytest
from pantheon.calibration.probes import DIMENSIONS, load_probes


def test_load_probes_default():
    p = load_probes()
    assert p.schema_version == "1.0"
    assert set(p.questions.keys()) == set(DIMENSIONS)


def test_each_dimension_has_questions():
    p = load_probes()
    for dim in DIMENSIONS:
        qs = p.for_dimension(dim)
        assert len(qs) >= 6, f"{dim} has only {len(qs)} probes"
        for q in qs:
            assert isinstance(q, str) and q.endswith("?")


def test_dimensions_order_is_canonical():
    """Order of DIMENSIONS is part of the contract — calibration replay
    relies on it for deterministic output."""
    assert DIMENSIONS == (
        "ethics", "governance", "education", "business",
        "technology", "divination", "emotion",
    )


def test_missing_dimension_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: '1.0'\nethics: ['q?']\ngovernance: ['q?']\n",
        encoding="utf-8",
    )
    # missing the other 5 dimensions
    with pytest.raises(ValueError, match="missing questions"):
        load_probes(bad)
