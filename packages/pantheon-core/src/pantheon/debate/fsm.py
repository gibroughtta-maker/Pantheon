"""Debate FSM — explicit state names and legal transitions.

Plan §4.1:
  CREATED → OPENING → CROSS_EXAM → REBUTTAL → SYNTHESIS* → VERDICT → CLOSED
                                                  (loop ≤ 3)
  any → DEGRADED on TIMEOUT / BUDGET / GATEWAY_FAIL
"""
from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class Phase(str, Enum):
    CREATED = "created"
    OPENING = "opening"
    CROSS_EXAM = "cross_exam"
    REBUTTAL = "rebuttal"
    SYNTHESIS = "synthesis"
    VERDICT = "verdict"
    CLOSED = "closed"
    DEGRADED = "degraded"


class PhaseTransition(NamedTuple):
    src: Phase
    dst: Phase


_LEGAL: set[PhaseTransition] = {
    PhaseTransition(Phase.CREATED, Phase.OPENING),
    PhaseTransition(Phase.OPENING, Phase.CROSS_EXAM),
    PhaseTransition(Phase.CROSS_EXAM, Phase.REBUTTAL),
    PhaseTransition(Phase.REBUTTAL, Phase.SYNTHESIS),
    PhaseTransition(Phase.REBUTTAL, Phase.VERDICT),  # synthesis can be skipped
    PhaseTransition(Phase.SYNTHESIS, Phase.SYNTHESIS),  # synthesis loop
    PhaseTransition(Phase.SYNTHESIS, Phase.VERDICT),
    PhaseTransition(Phase.VERDICT, Phase.CLOSED),
}

# Any active phase can degrade.
for _p in (
    Phase.OPENING,
    Phase.CROSS_EXAM,
    Phase.REBUTTAL,
    Phase.SYNTHESIS,
    Phase.VERDICT,
):
    _LEGAL.add(PhaseTransition(_p, Phase.DEGRADED))
_LEGAL.add(PhaseTransition(Phase.DEGRADED, Phase.CLOSED))


def valid_transitions() -> set[PhaseTransition]:
    return set(_LEGAL)


def is_legal(src: Phase, dst: Phase) -> bool:
    return PhaseTransition(src, dst) in _LEGAL
