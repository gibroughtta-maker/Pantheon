"""accept_disclaimer() gating + region check + persona registration."""
from __future__ import annotations

import importlib

import pytest


def _fresh_module():
    """Reload the module so global `_DISCLAIMER_ACCEPTED` resets between tests."""
    import pantheon_pack_founders
    return importlib.reload(pantheon_pack_founders)


def test_register_without_accept_raises(monkeypatch):
    monkeypatch.delenv("PANTHEON_REGION", raising=False)
    ppf = _fresh_module()
    with pytest.raises(ppf.FoundersPackUnavailable, match="accept_disclaimer"):
        ppf.register()


def test_provide_personas_empty_without_accept(monkeypatch):
    monkeypatch.delenv("PANTHEON_REGION", raising=False)
    ppf = _fresh_module()
    assert ppf.provide_personas() == []


def test_region_cn_blocks(monkeypatch):
    monkeypatch.setenv("PANTHEON_REGION", "cn")
    ppf = _fresh_module()
    with pytest.raises(ppf.FoundersPackUnavailable, match="region"):
        ppf.accept_disclaimer()


def test_accept_then_register(monkeypatch):
    monkeypatch.delenv("PANTHEON_REGION", raising=False)
    ppf = _fresh_module()
    ppf.accept_disclaimer()
    n = ppf.register()
    assert n == 3
    # Personas are now in the global registry.
    from pantheon import registry
    for pid in ("jesus", "muhammad", "buddha"):
        p = registry.get(pid)
        assert p.spec.id == pid


def test_personas_have_corpus_manifest_pointing_at_upstream(monkeypatch):
    """Each persona ships a manifest.yaml with upstream URLs but NO
    canonical text inline."""
    import yaml
    from pathlib import Path

    monkeypatch.delenv("PANTHEON_REGION", raising=False)
    ppf = _fresh_module()
    ppf.accept_disclaimer()
    # Locate the personas dir of the package.
    root = Path(ppf.__file__).parent.parent.parent / "personas"
    if not root.exists():
        root = Path(ppf.__file__).parent / "personas"
    assert root.exists()
    for pid in ("jesus", "muhammad", "buddha"):
        manifest = root / pid / "corpus" / "manifest.yaml"
        assert manifest.exists()
        m = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        assert m["persona"] == pid
        # At least one source with upstream URL.
        assert any(s.get("upstream") for s in m.get("sources", []))
        # No canonical-text .txt files alongside the manifest.
        canonical = [
            f for f in (root / pid / "corpus").rglob("*.txt")
        ]
        assert canonical == [], (
            f"{pid}: corpus has embedded text files {canonical}; "
            "this pack must rely on `pantheon corpus fetch`"
        )


def test_verdict_disclaimer_is_a_string():
    ppf = _fresh_module()
    assert isinstance(ppf.VERDICT_DISCLAIMER, str)
    assert len(ppf.VERDICT_DISCLAIMER) > 50
