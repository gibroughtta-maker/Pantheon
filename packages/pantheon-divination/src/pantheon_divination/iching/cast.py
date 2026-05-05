"""Three-coin method for casting a hexagram.

Per the traditional rules:
  - Throw three coins; heads=3 (yang), tails=2 (yin).
  - Sum: 6 (old yin), 7 (young yang), 8 (young yin), 9 (old yang).
  - Old lines are CHANGING — they yield the second hexagram.
  - Repeat 6 times (bottom→top).

The cast is fully deterministic given (question, seed). Two seeds chosen
to be far apart in `random.Random.seed` space will produce different
hexagrams, but two identical seeds always produce the same cast.
"""
from __future__ import annotations

import hashlib
import random

from pantheon_divination import _ensure_accepted
from pantheon_divination.iching.data import Hexagram, hexagram_by_lines
from pantheon_divination.types import DivinationLine, DivinationResult, FormatHelpers


def _coin_throw(rng: random.Random) -> int:
    """One coin: 3 for heads (yang), 2 for tails (yin)."""
    return 3 if rng.random() < 0.5 else 2


def _three_coins(rng: random.Random) -> int:
    """Sum of three coins → 6, 7, 8, or 9."""
    return _coin_throw(rng) + _coin_throw(rng) + _coin_throw(rng)


# Traditional names for the six line positions.
_LINE_NAMES_ZH = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]
_LINE_NAMES_EN = ["Initial", "Second", "Third", "Fourth", "Fifth", "Top"]


def _seed_for(question: str, seed: int) -> int:
    """Combine question and seed into a single 64-bit RNG seed.
    Pure function — deterministic and side-effect-free."""
    h = hashlib.sha256(f"{seed}|{question}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def cast(question: str, *, seed: int = 0) -> DivinationResult:
    """Cast an I Ching hexagram for the given question.

    Returns a DivinationResult containing:
      - the present hexagram (`primary`)
      - the transformed hexagram (`secondary`) if any line is changing
      - one DivinationLine per of the 6 throws
    """
    _ensure_accepted()
    rng = random.Random(_seed_for(question, seed))

    throws = [_three_coins(rng) for _ in range(6)]    # bottom→top
    present_lines = [1 if t in (7, 9) else 0 for t in throws]
    transformed_lines = [
        (1 - v) if t in (6, 9) else v
        for v, t in zip(present_lines, throws)
    ]
    changing = [t in (6, 9) for t in throws]

    present = hexagram_by_lines(present_lines)
    transformed: Hexagram | None = (
        hexagram_by_lines(transformed_lines)
        if any(changing)
        else None
    )

    div_lines: list[DivinationLine] = []
    for i in range(6):
        name = f"{_LINE_NAMES_ZH[i]} ({_LINE_NAMES_EN[i]})"
        is_yang = present_lines[i] == 1
        marker = "⚊" if is_yang else "⚋"
        if changing[i]:
            marker += " (changing)"
        div_lines.append(
            DivinationLine(
                position=name,
                text=marker,
                is_changing=changing[i],
                extra={"throw_value": str(throws[i])},
            )
        )

    primary = (
        f"#{present.number} {present.chinese} ({present.pinyin}) — "
        f"{present.english}"
    )
    secondary = ""
    if transformed:
        secondary = (
            f"→ #{transformed.number} {transformed.chinese} "
            f"({transformed.pinyin}) — {transformed.english}"
        )

    return DivinationResult(
        method="iching",
        question=question,
        seed=seed,
        headline_zh=f"{present.chinese}卦",
        headline_en=present.english,
        primary=primary,
        secondary=secondary,
        judgment=present.judgement,
        image=present.image,
        lines=div_lines,
        structured={
            "present_number": str(present.number),
            "present_chinese": present.chinese,
            "present_english": present.english,
            "transformed_number": str(transformed.number) if transformed else "",
            "transformed_chinese": transformed.chinese if transformed else "",
            "upper_trigram": present.upper_trigram,
            "lower_trigram": present.lower_trigram,
            "glyph": FormatHelpers.hexagram_unicode(present_lines[::-1]),
        },
        raw_state={
            "throws": throws,
            "present_lines": present_lines,
            "transformed_lines": transformed_lines if any(changing) else None,
            "changing_indices": [i for i, c in enumerate(changing) if c],
        },
    )
