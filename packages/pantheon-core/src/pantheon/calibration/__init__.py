"""Skill calibration pipeline.

Distill a persona's 7-dimensional skill vector from its corpus + a panel of
LLM judges, instead of hand-filling numbers.

Design (plan §F):
  L2 retrieval: 6 prototype questions per dimension; score = mean similarity
                of best corpus match per question.
  L4 pairwise:  pairwise LLM-judge tournament against anchor personas; resolve
                via Bradley-Terry to a [0,1] score per dimension.
  Fusion:       weighted average; if |L2 - L4| > sigma_threshold, the
                dimension is flagged for manual review.

All LLM calls go through the same Gateway used by the debate engine, so
calibrations are recordable and replayable like any other run.
"""
from pantheon.calibration.audit import write_calibration_metadata
from pantheon.calibration.l2_retrieval import L2Result, score_l2
from pantheon.calibration.l4_pairwise import L4Result, score_l4
from pantheon.calibration.probes import DIMENSIONS, Probes, load_probes
from pantheon.calibration.runner import CalibrationResult, run_calibration

__all__ = [
    "CalibrationResult",
    "DIMENSIONS",
    "L2Result",
    "L4Result",
    "Probes",
    "load_probes",
    "run_calibration",
    "score_l2",
    "score_l4",
    "write_calibration_metadata",
]
