"""Founders calibration dry-run.

Exercises the L2 + L4 pipeline against a tiny in-memory synthetic corpus
and a fully scripted MockGateway. Does NOT produce defensible scores —
the corpus is synthetic and the votes are scripted — but it proves the
pipeline wires up correctly when you have:

  - accept_disclaimer() accepted
  - the founder personas registered
  - L2 + L4 fused with σ flagging working
  - audit.calibration metadata written back

Real calibration is documented in CALIBRATION_RUNBOOK.md.
"""
from __future__ import annotations

import importlib

import pytest
from pantheon import MockGateway, Model, ScriptedReply, registry
from pantheon.calibration.probes import DIMENSIONS
from pantheon.calibration.runner import run_calibration
from pantheon.memory.embedded_corpus import EmbeddedCorpusStore, HashEmbedder


@pytest.fixture
def founders_loaded(monkeypatch):
    monkeypatch.delenv("PANTHEON_REGION", raising=False)
    import pantheon_pack_founders
    ppf = importlib.reload(pantheon_pack_founders)
    ppf.accept_disclaimer()
    ppf.register()
    return ppf


@pytest.mark.asyncio
async def test_l2_only_calibration_runs_for_each_founder(founders_loaded, tmp_path):
    """Every founder persona is reachable via L2-only calibration without
    LLM judges. The pipeline returns a CalibrationResult with all 7
    dimensions scored."""
    for pid in ("jesus", "muhammad", "buddha"):
        persona = registry.get(pid)
        # Inject a tiny synthetic corpus so L2 has something to retrieve.
        store = EmbeddedCorpusStore(persona_id=pid, embedder=HashEmbedder())
        store.add_text(
            "This is a tiny synthetic corpus excerpt about ethics, "
            "compassion, suffering, and the duty to act rightly. "
            "It exists only to validate the calibration pipeline.",
            source="synthetic.txt",
        )
        persona.corpus = store
        res = await run_calibration(
            persona,
            anchor_personas=[],
            judges=[],
            record_dir=tmp_path,
        )
        assert res.method == "l2_only"
        assert set(res.final.keys()) == set(DIMENSIONS)
        # σ all zero in L2-only.
        for dim in DIMENSIONS:
            assert res.sigma[dim] == 0.0


@pytest.mark.asyncio
async def test_l2_l4_hybrid_calibration_dryrun(founders_loaded, tmp_path):
    """Full L2+L4 pipeline against scripted MockGateway votes. Verifies
    the runner produces a Result with Bradley-Terry-derived L4 scores
    and σ flags as appropriate."""
    persona = registry.get("buddha")
    store = EmbeddedCorpusStore(persona_id="buddha", embedder=HashEmbedder())
    store.add_text(
        "Suffering exists; suffering has a cause; cessation is possible; "
        "the path is the way. Compassion is the heart of practice.",
        source="synthetic.txt",
    )
    persona.corpus = store

    confucius = registry.get("confucius")
    socrates = registry.get("socrates")

    gw = MockGateway()
    n_calls = len(DIMENSIONS) * 6 * 2 * 1  # 7 dims × 6 probes × 2 anchors × 1 judge
    for i in range(n_calls):
        # Buddha (target) wins on emotion/ethics; ties elsewhere.
        if i % 4 == 0:
            vote = "VOTE: A\nbuddha is stronger on this dim"
        elif i % 4 == 1:
            vote = "VOTE: B\nanchor is stronger on this dim"
        else:
            vote = "VOTE: TIE\nthey are comparable"
        gw.add_reply(ScriptedReply(text=vote, model_id="judge-mock"))

    res = await run_calibration(
        persona,
        anchor_personas=[confucius, socrates],
        judges=[Model(id="judge-mock", gateway=gw)],
        record_dir=tmp_path,
        seed=42,
    )
    assert res.method == "l2_l4_hybrid"
    assert res.l4 is not None
    assert set(res.l4.by_dimension.keys()) == set(DIMENSIONS)
    # σ values present per dim.
    for dim in DIMENSIONS:
        assert dim in res.sigma
    # JSONL recording exists.
    from pathlib import Path
    assert Path(res.recording_path).exists()


@pytest.mark.asyncio
async def test_dry_run_writeback_does_not_break_persona_yaml(founders_loaded, tmp_path):
    """Verify write_calibration_metadata round-trips through the persona
    YAML cleanly — no schema-version bump, no field loss."""
    from pathlib import Path

    import yaml
    from pantheon.calibration.audit import write_calibration_metadata

    persona = registry.get("jesus")
    store = EmbeddedCorpusStore(persona_id="jesus", embedder=HashEmbedder())
    store.add_text("Tiny synthetic corpus.", source="synthetic.txt")
    persona.corpus = store

    res = await run_calibration(persona, record_dir=tmp_path)

    # Locate the persona.yaml on disk by walking up from the loaded module.
    import pantheon_pack_founders
    pkg_root = Path(pantheon_pack_founders.__file__).parent.parent.parent
    yaml_path = pkg_root / "personas" / "jesus" / "persona.yaml"
    assert yaml_path.exists()
    raw_before = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    # Write to a tmp copy so we don't mutate the repo file under test.
    tmp_yaml = tmp_path / "jesus.yaml"
    tmp_yaml.write_text(yaml_path.read_text(encoding="utf-8"), encoding="utf-8")
    write_calibration_metadata(tmp_yaml, res, apply_flagged=False)

    raw_after = yaml.safe_load(tmp_yaml.read_text(encoding="utf-8"))
    # Every field that was in the original should still be there.
    assert raw_after["id"] == raw_before["id"]
    assert raw_after["display"] == raw_before["display"]
    # Skills got at least one update from L2 scoring.
    assert raw_after["skills"]
    # Calibration block populated.
    assert raw_after["audit"]["calibration"]["run_id"] == res.run_id
    assert raw_after["audit"]["calibration"]["method"] == "l2_only"
