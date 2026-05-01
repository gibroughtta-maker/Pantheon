"""Streaming debate events emitted by `Session.stream()`."""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class _EventBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    seq: int  # monotonic, starts at 0


class SpeechEvent(_EventBase):
    type: Literal["speech"] = "speech"
    seat: int
    persona_id: str
    phase: str
    text: str
    model_id: str


class PhaseBoundaryEvent(_EventBase):
    type: Literal["phase_boundary"] = "phase_boundary"
    from_phase: str
    to_phase: str


class SwapEvent(_EventBase):
    type: Literal["swap"] = "swap"
    seat: int
    kind: Literal["persona", "model", "memory"]
    from_id: str
    to_id: str
    handoff_statement: str | None = None  # for persona swaps


class SystemEvent(_EventBase):
    """Moderator or Auditor side-channel notes."""

    type: Literal["system"] = "system"
    role: Literal["moderator", "oracle", "auditor", "framework"]
    message: str


class VerdictEvent(_EventBase):
    type: Literal["verdict"] = "verdict"
    # The full Verdict is large; we ship a reference and the consumer pulls it
    # via Session.verdict(). Streaming consumers see a marker.
    debate_id: str


DebateEvent = Annotated[
    Union[SpeechEvent, PhaseBoundaryEvent, SwapEvent, SystemEvent, VerdictEvent],
    Field(discriminator="type"),
]
