"""易经 (Yijing / I Ching) divination — 64 hexagrams, three-coin method.

Public API:

    pd.iching.cast(question, seed) -> DivinationResult

The cast is fully deterministic given (question, seed): three coins are
"thrown" six times via a seeded RNG; each toss yields 6, 7, 8, or 9
(young yin, young yang, old yang, old yin) per the traditional rules. Old
lines are changing lines; the result includes both the present hexagram
and the transformed (after-changes) hexagram.

Hexagram metadata (number, Chinese name, English name, Wilhelm-style
keywords) ships in `data/hexagrams.json` (Public Domain — the 易经
itself is BCE; English keywords are common-knowledge translations).
"""
from pantheon_divination.iching.cast import cast
from pantheon_divination.iching.data import load_hexagrams

__all__ = ["cast", "load_hexagrams"]
