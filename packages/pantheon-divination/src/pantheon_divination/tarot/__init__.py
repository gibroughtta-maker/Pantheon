"""Tarot divination — 78-card deck (22 Major Arcana + 56 Minor Arcana),
default Celtic Cross spread.

Public API:

    pd.tarot.cast(question, spread="celtic_cross", seed)
"""
from pantheon_divination.tarot.cast import SPREADS, cast
from pantheon_divination.tarot.data import load_cards

__all__ = ["SPREADS", "cast", "load_cards"]
