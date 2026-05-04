"""bench/models.yaml loader + capability lookup."""
from __future__ import annotations

import pytest

from pantheon.bench import capability_for, load_models_yaml, models_registry


def test_bundled_models_yaml_loads():
    reg = load_models_yaml()
    assert "claude-opus-4-7" in reg
    assert "deepseek-chat" in reg
    assert "gpt-4o" in reg


def test_capability_for_known_model():
    cap = capability_for("claude-opus-4-7")
    assert cap.model_id == "claude-opus-4-7"
    assert 0.9 <= cap.for_dimension("ethics") <= 1.0
    assert 0.0 <= cap.cultural_depth.get("zh", 0.0) <= 1.0


def test_capability_for_unknown_returns_default():
    cap = capability_for("not-a-real-model")
    for d in ["ethics", "business", "technology", "emotion"]:
        assert cap.for_dimension(d) == 0.5


def test_overall_geometric_mean():
    cap = capability_for("claude-opus-4-7")
    assert 0.5 < cap.overall < 1.0


def test_local_yaml_overrides_bundled(tmp_path, monkeypatch):
    # Make a tiny local override and point the env var at it.
    local = tmp_path / "models.local.yaml"
    local.write_text(
        "schema_version: '1.0'\n"
        "models:\n"
        "  claude-opus-4-7:\n"
        "    ethics: 0.10\n"
        "    business: 0.10\n"
        "    education: 0.10\n"
        "    governance: 0.10\n"
        "    technology: 0.10\n"
        "    divination: 0.10\n"
        "    emotion: 0.10\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PANTHEON_MODELS_FILE", str(local))
    models_registry.cache_clear()
    try:
        cap = capability_for("claude-opus-4-7")
        assert cap.for_dimension("ethics") == 0.10
        cap2 = capability_for("gpt-4o")
        assert cap2.for_dimension("ethics") > 0.5
    finally:
        models_registry.cache_clear()


def test_chinese_cultural_depth_present():
    """deepseek-chat should be the strongest Chinese-fluency model in the
    seed file."""
    deepseek = capability_for("deepseek-chat")
    opus = capability_for("claude-opus-4-7")
    assert deepseek.cultural_depth["zh"] >= opus.cultural_depth["zh"]
