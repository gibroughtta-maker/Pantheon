"""Persona loader and registry contracts."""
from __future__ import annotations

import pytest

from pantheon import registry
from pantheon.types.persona import PersonaSpec


def test_three_builtin_personas_registered():
    ids = sorted(p.id for p in registry.all())
    assert {"confucius", "socrates", "naval"}.issubset(set(ids))


def test_persona_spec_validates_skills_bounded():
    raw = {
        "id": "bad",
        "display": {"en": "Bad"},
        "model_preference": {"primary": "x"},
        "skills": {"ethics": 1.5},
    }
    with pytest.raises(ValueError):
        PersonaSpec.model_validate(raw)


def test_persona_id_must_be_snake_case():
    raw = {
        "id": "Bad-Id",
        "display": {"en": "Bad"},
        "model_preference": {"primary": "x"},
    }
    with pytest.raises(ValueError):
        PersonaSpec.model_validate(raw)


def test_confucius_has_audit_metadata():
    p = registry.get("confucius")
    assert p.spec.audit.cultural_sensitivity_score is not None
    assert "@wendy" in p.spec.audit.reviewed_by


def test_persona_system_prompt_includes_marker():
    p = registry.get("socrates")
    sp = p.system_prompt()
    assert "[persona:socrates]" in sp


def test_persona_system_prompt_with_instance_suffix():
    p = registry.get("confucius")
    sp = p.system_prompt(instance_suffix="2")
    assert "[persona:confucius#2]" in sp
