"""Debate engine — FSM, phase strategies, session orchestrator."""
from pantheon.debate.fsm import Phase, PhaseTransition, valid_transitions
from pantheon.debate.phases import (
    CrossExamPhase,
    OpeningPhase,
    PhaseContext,
    PhaseStrategy,
    RebuttalPhase,
    SynthesisPhase,
    VerdictPhase,
)
from pantheon.debate.session import Session

__all__ = [
    "CrossExamPhase",
    "OpeningPhase",
    "Phase",
    "PhaseContext",
    "PhaseStrategy",
    "PhaseTransition",
    "RebuttalPhase",
    "Session",
    "SynthesisPhase",
    "VerdictPhase",
    "valid_transitions",
]
