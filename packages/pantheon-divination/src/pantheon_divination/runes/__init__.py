"""Norse Elder Futhark — 24 runes, three-rune spread by default.

Casting: deterministic from (question, seed). Three runes drawn without
replacement, each with a 50/50 reversed (merkstave) flag.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from pantheon_divination import _ensure_accepted
from pantheon_divination.types import DivinationLine, DivinationResult


@dataclass(frozen=True)
class Rune:
    name: str
    symbol: str
    upright: str
    reversed: str


# Elder Futhark, 24 runes (Aett 1, 2, 3). Public domain symbology.
_RUNES: tuple[Rune, ...] = (
    Rune("Fehu",     "ᚠ", "wealth, mobile resources, success",   "loss, greed, blocked flow"),
    Rune("Uruz",     "ᚢ", "raw vitality, primal strength",       "weakness, missed opportunity"),
    Rune("Thurisaz", "ᚦ", "thorn, conflict, defensive force",    "spite, malice"),
    Rune("Ansuz",    "ᚨ", "wisdom, communication, signal",       "deception, miscommunication"),
    Rune("Raidho",   "ᚱ", "journey, motion, ritual order",       "stagnation, unwanted travel"),
    Rune("Kenaz",    "ᚲ", "torch, knowledge through craft",      "darkness, withheld knowledge"),
    Rune("Gebo",     "ᚷ", "gift, exchange, alliance",            "(no reversed; balance disturbed)"),
    Rune("Wunjo",    "ᚹ", "joy, harmony, kinship",               "discord, sorrow"),
    Rune("Hagalaz",  "ᚺ", "hail, sudden disruption (necessary)", "(no reversed; uncontrolled chaos)"),
    Rune("Nauthiz",  "ᚾ", "need, constraint, hardship as teacher","unmet need, despair"),
    Rune("Isa",      "ᛁ", "ice, stillness, pause",               "(no reversed; deep freeze)"),
    Rune("Jera",     "ᛃ", "harvest, year, cycles bearing fruit", "(no reversed; bad season)"),
    Rune("Eihwaz",   "ᛇ", "yew, endurance, axis between worlds", "(no reversed; obstinacy)"),
    Rune("Perthro",  "ᛈ", "lot-cup, fate, hidden pattern",       "stagnation, secrets revealed badly"),
    Rune("Algiz",    "ᛉ", "elk, protection, sacred boundary",    "vulnerability, taboo broken"),
    Rune("Sowilo",   "ᛊ", "sun, victory, life force",            "(no reversed; clouded victory)"),
    Rune("Tiwaz",    "ᛏ", "Tyr, justice, sacrifice for principle","injustice, lost cause"),
    Rune("Berkano",  "ᛒ", "birch, growth, mother, beginnings",   "stagnation, family trouble"),
    Rune("Ehwaz",    "ᛖ", "horse, partnership, motion together", "discord, broken trust"),
    Rune("Mannaz",   "ᛗ", "humanity, the self in society",       "isolation, depression"),
    Rune("Laguz",    "ᛚ", "water, flow, intuition",              "fear, blocked instinct"),
    Rune("Ingwaz",   "ᛜ", "Ing, fertility, gestation",           "(no reversed; stunted potential)"),
    Rune("Dagaz",    "ᛞ", "day, awakening, breakthrough",        "(no reversed; missed dawn)"),
    Rune("Othala",   "ᛟ", "ancestral land, heritage, home",      "rootlessness, inherited problems"),
)

# Some runes traditionally have no reversed meaning; we still allow drawing
# reversed for symmetry but report the same upright keyword in those cases.

SPREADS = {
    "three_rune":   [("Past", "what shaped you"),
                     ("Present", "what is now"),
                     ("Future", "what comes")],
    "single_rune":  [("Stone", "for the question")],
    "norns_spread": [("Urd", "what was"),
                     ("Verdandi", "what is"),
                     ("Skuld", "what shall be")],
}


def _seed_for(question: str, spread: str, seed: int) -> int:
    h = hashlib.sha256(f"{seed}|{spread}|{question}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def cast(question: str, *, spread: str = "three_rune", seed: int = 0) -> DivinationResult:
    _ensure_accepted()
    if spread not in SPREADS:
        raise ValueError(f"unknown spread {spread!r}; known: {sorted(SPREADS)}")
    rng = random.Random(_seed_for(question, spread, seed))
    pool = list(_RUNES)
    rng.shuffle(pool)
    div_lines: list[DivinationLine] = []
    drawn: list[tuple[Rune, bool, tuple[str, str]]] = []
    for pos in SPREADS[spread]:
        rune = pool.pop()
        reversed_ = rng.random() < 0.5
        drawn.append((rune, reversed_, pos))
        meaning = rune.reversed if reversed_ else rune.upright
        div_lines.append(
            DivinationLine(
                position=f"{pos[0]} — {pos[1]}",
                text=f"{rune.name} {rune.symbol} {'(reversed)' if reversed_ else ''} — {meaning}",
                is_reversed=reversed_,
                extra={"symbol": rune.symbol},
            )
        )
    primary = drawn[0][0]
    return DivinationResult(
        method="runes",
        question=question,
        seed=seed,
        headline_zh=primary.name,
        headline_en=primary.name,
        primary=f"{primary.name} {primary.symbol}",
        secondary=drawn[-1][0].name if len(drawn) > 1 else "",
        judgment=primary.upright,
        image=primary.symbol,
        lines=div_lines,
        structured={"spread": spread, "n_runes": str(len(drawn))},
        raw_state={
            "drawn_names": [r.name for r, _, _ in drawn],
            "reversed_flags": [rev for _, rev, _ in drawn],
        },
    )


__all__ = ["Rune", "SPREADS", "cast"]
