"""Relay mode — when an agent swaps persona mid-debate, the new persona must
open with a handoff statement that references the prior speaker. This module
composes that statement so the convention is enforced framework-side rather
than relying on prompts alone."""
from __future__ import annotations


def compose_handoff(from_persona_display: str, to_persona_display: str) -> str:
    """Return a one-line opener the new persona is forced to begin with."""
    # Bilingual opener; downstream prompt will continue from here.
    return (
        f"先师{from_persona_display}方才所言，本{to_persona_display}有不同看法。 "
        f"(Taking the floor from {from_persona_display}, this is "
        f"{to_persona_display} continuing.) "
    )
