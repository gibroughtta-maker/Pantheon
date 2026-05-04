"""accept_disclaimer() gate + region restriction."""
from __future__ import annotations

import importlib

import pytest


def _fresh():
    import pantheon_divination
    return importlib.reload(pantheon_divination)


def test_iching_raises_without_accept(monkeypatch):
    monkeypatch.delenv("PANTHEON_REGION", raising=False)
    pd = _fresh()
    with pytest.raises(pd.DivinationUnavailable, match="accept_disclaimer"):
        pd.iching.cast(question="?", seed=1)


def test_tarot_raises_without_accept(monkeypatch):
    monkeypatch.delenv("PANTHEON_REGION", raising=False)
    pd = _fresh()
    with pytest.raises(pd.DivinationUnavailable, match="accept_disclaimer"):
        pd.tarot.cast(question="?", seed=1)


def test_region_cn_blocks_disclaimer(monkeypatch):
    monkeypatch.setenv("PANTHEON_REGION", "cn")
    monkeypatch.delenv("PANTHEON_DIVINATION_REGION_OVERRIDE", raising=False)
    pd = _fresh()
    with pytest.raises(pd.DivinationUnavailable, match="region=cn"):
        pd.accept_disclaimer()


def test_region_cn_override_allows(monkeypatch):
    monkeypatch.setenv("PANTHEON_REGION", "cn")
    monkeypatch.setenv("PANTHEON_DIVINATION_REGION_OVERRIDE", "1")
    pd = _fresh()
    pd.accept_disclaimer()  # does not raise


def test_disclaimer_text_present():
    pd = _fresh()
    assert "Pantheon divination" in pd.DISCLAIMER_TEXT
    assert "NOT" in pd.DISCLAIMER_TEXT
