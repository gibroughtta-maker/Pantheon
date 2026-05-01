"""Persona schema (v1.0).

Persona definition is **stateless** and **pure data**. No LLM client lives here,
no conversation history. An Agent wears a Persona; the Persona itself is
shareable, hashable by id, and (in production) signed in a pack manifest.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CorpusSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    weight: float = 1.0
    license: str = "Unknown"


class CorpusRetrievalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    top_k: int = 4
    min_score: float = 0.5


class CorpusConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[CorpusSource] = Field(default_factory=list)
    retrieval: CorpusRetrievalConfig = Field(default_factory=CorpusRetrievalConfig)
    quote_policy: Literal["verbatim_or_paraphrase", "paraphrase_only", "free"] = (
        "verbatim_or_paraphrase"
    )


class Personality(BaseModel):
    model_config = ConfigDict(extra="forbid")
    core_values: list[str] = Field(default_factory=list)
    rhetorical_style: str = ""
    catchphrases: list[str] = Field(default_factory=list)


class DebateStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aggression: float = 0.5
    yielding: float = 0.5
    citation_density: float = 0.5

    @field_validator("aggression", "yielding", "citation_density")
    @classmethod
    def _bound(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("debate_style values must be in [0, 1]")
        return v


class ModelPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    primary: str
    fallback: str | None = None
    forbidden: list[str] = Field(default_factory=list)


class ManualOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float
    reason: str


class CalibrationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["hand_filled", "l2_only", "l4_only", "l2_l4_hybrid"] = "hand_filled"
    run_id: str | None = None
    run_at: str | None = None
    judges: list[str] = Field(default_factory=list)
    anchors_used: list[str] = Field(default_factory=list)
    sigma_per_dim: dict[str, float] = Field(default_factory=dict)
    manual_overrides: dict[str, ManualOverride] = Field(default_factory=dict)


class AuditMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewed_by: list[str] = Field(default_factory=list)
    cultural_sensitivity_score: float | None = None
    last_audit: str | None = None
    known_biases: list[str] = Field(default_factory=list)
    calibration: CalibrationMetadata = Field(default_factory=CalibrationMetadata)


class Relations(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contemporaries: list[str] = Field(default_factory=list)
    opponents: list[str] = Field(default_factory=list)
    successors: list[str] = Field(default_factory=list)


class DisplayName(BaseModel):
    model_config = ConfigDict(extra="allow")
    zh: str | None = None
    en: str | None = None


class PersonaSpec(BaseModel):
    """The on-disk YAML schema for a persona."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    id: str
    display: DisplayName
    era: str = ""
    school: str = ""
    language_preference: list[str] = Field(default_factory=lambda: ["en"])

    personality: Personality = Field(default_factory=Personality)
    skills: dict[str, float] = Field(default_factory=dict)
    debate_style: DebateStyle = Field(default_factory=DebateStyle)
    model_preference: ModelPreference

    corpus: CorpusConfig = Field(default_factory=CorpusConfig)

    extends: str | None = None
    variant_tag: str | None = None

    audit: AuditMetadata = Field(default_factory=AuditMetadata)
    relations: Relations = Field(default_factory=Relations)

    system_prompt: str = ""
    system_prompt_file: str | None = None
    historical_sources: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id_snake(cls, v: str) -> str:
        if not v or not v.replace("_", "").isalnum():
            raise ValueError("persona id must be snake_case alphanumeric")
        return v

    @field_validator("skills")
    @classmethod
    def _skills_bounded(cls, v: dict[str, float]) -> dict[str, float]:
        for k, val in v.items():
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"skill {k!r} must be in [0, 1]")
        return v
