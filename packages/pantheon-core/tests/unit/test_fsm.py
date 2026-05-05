"""FSM legality and transition rules."""
from __future__ import annotations

import pytest
from pantheon.debate.fsm import Phase, is_legal


@pytest.mark.parametrize(
    "src,dst,legal",
    [
        (Phase.CREATED, Phase.OPENING, True),
        (Phase.OPENING, Phase.CROSS_EXAM, True),
        (Phase.CROSS_EXAM, Phase.REBUTTAL, True),
        (Phase.REBUTTAL, Phase.SYNTHESIS, True),
        (Phase.REBUTTAL, Phase.VERDICT, True),
        (Phase.SYNTHESIS, Phase.SYNTHESIS, True),
        (Phase.SYNTHESIS, Phase.VERDICT, True),
        (Phase.VERDICT, Phase.CLOSED, True),
        (Phase.OPENING, Phase.DEGRADED, True),
        (Phase.DEGRADED, Phase.CLOSED, True),
        # Illegal:
        (Phase.CREATED, Phase.CROSS_EXAM, False),
        (Phase.OPENING, Phase.REBUTTAL, False),
        (Phase.OPENING, Phase.VERDICT, False),
        (Phase.CLOSED, Phase.OPENING, False),
        (Phase.CLOSED, Phase.DEGRADED, False),
    ],
)
def test_transitions(src: Phase, dst: Phase, legal: bool):
    assert is_legal(src, dst) is legal
