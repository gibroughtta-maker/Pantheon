"""Verdict and supporting types — see plan §七."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ClaimType = Literal["quote", "inference", "principle", "speculation"]
GroundingTag = Literal["verified", "unverified", "no_corpus"]


class ClaimRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str


class Claim(BaseModel):
    """An assertion made by a speaker, tracked by Moderator/Auditor."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    speaker: str  # e.g. "seat#1" or "confucius#1"
    text: str
    type: ClaimType = "inference"
    source: str | None = None
    grounding_score: float = 0.5
    grounding_tag: GroundingTag = "no_corpus"
    challenged_by: list[ClaimRef] = Field(default_factory=list)
    supported_by: list[ClaimRef] = Field(default_factory=list)


class ConsensusPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str
    supporters: list[str]
    weight: float


class MinorityPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str
    holder: str
    rationale: str


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str
    rationale: str
    advocate: str | None = None


class SpeakerSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seat: int
    persona_id: str  # latest persona at end of debate
    weight: float
    speech_count: int
    avg_grounding: float


class RelayLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seat: int
    from_persona: str
    to_persona: str
    at_phase: str


class CostBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_usd: float = 0.0
    total_calls: int = 0
    by_seat: dict[int, float] = Field(default_factory=dict)
    by_model: dict[str, float] = Field(default_factory=dict)


class QualityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    avg_grounding_score: float = 0.0
    unverified_quote_count: int = 0
    devil_advocate_invoked: bool = False
    persona_swap_warnings: list[str] = Field(default_factory=list)


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    session_id: str
    debate_id: str
    question: str
    topic_tags: dict[str, float] = Field(default_factory=dict)

    consensus: list[ConsensusPoint] = Field(default_factory=list)
    minority_opinion: list[MinorityPoint] = Field(default_factory=list)
    action_items: list[ActionItem] | None = None

    speaker_summary: list[SpeakerSummary] = Field(default_factory=list)
    persona_relay_log: list[RelayLogEntry] = Field(default_factory=list)

    quality: QualityMetrics = Field(default_factory=QualityMetrics)
    no_consensus: bool = False
    consensus_robustness: Literal["high", "medium", "low"] = "medium"

    trace_id: str = ""
    cost: CostBreakdown = Field(default_factory=CostBreakdown)
    duration_ms: int = 0
    model_calls: int = 0

    disclaimer: str = (
        "本结果由多 LLM 辩论生成。引文已经 corpus 校验，但仍可能存在偏差。"
        "本结果不构成医疗、法律、财务、心理健康建议。"
    )
