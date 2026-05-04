"""Tarot deal — Celtic Cross by default, but pluggable.

The cast is fully deterministic given (question, spread, seed). Cards
are drawn without replacement from the 78-card deck; each card has a
50/50 chance of being reversed (drawn from the same RNG).
"""
from __future__ import annotations

import hashlib
import random

from pantheon_divination import _ensure_accepted
from pantheon_divination.tarot.data import TarotCard, load_cards
from pantheon_divination.types import DivinationLine, DivinationResult


# Spread definitions — list of position labels (English / Chinese / brief role).
SPREADS: dict[str, list[tuple[str, str, str]]] = {
    "celtic_cross": [
        ("Present",          "现状",      "the heart of the matter"),
        ("Challenge",        "挑战",      "what crosses you"),
        ("Foundation",       "根基",      "what underlies the present"),
        ("Past",             "过去",      "what is fading"),
        ("Crown",            "顶冠",      "the conscious aim above"),
        ("Future",           "未来",      "what approaches"),
        ("Self",             "自我",      "your stance"),
        ("Environment",      "外境",      "others & circumstance"),
        ("Hopes/Fears",      "希望与恐惧","what you wish and dread"),
        ("Outcome",          "结果",      "the most likely conclusion"),
    ],
    "three_card": [
        ("Past",    "过去", "where you came from"),
        ("Present", "现在", "where you stand"),
        ("Future",  "未来", "where you are heading"),
    ],
    "single": [
        ("Card", "牌", "for this question"),
    ],
}


def _seed_for(question: str, spread: str, seed: int) -> int:
    h = hashlib.sha256(f"{seed}|{spread}|{question}".encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big")


def cast(
    question: str,
    *,
    spread: str = "celtic_cross",
    seed: int = 0,
) -> DivinationResult:
    """Deal cards for a tarot spread."""
    _ensure_accepted()
    if spread not in SPREADS:
        raise ValueError(
            f"unknown spread {spread!r}; known: {sorted(SPREADS)}"
        )
    positions = SPREADS[spread]
    rng = random.Random(_seed_for(question, spread, seed))
    deck = list(load_cards())
    rng.shuffle(deck)
    drawn: list[tuple[TarotCard, bool, tuple[str, str, str]]] = []
    for pos in positions:
        card = deck.pop()
        reversed_ = rng.random() < 0.5
        drawn.append((card, reversed_, pos))

    div_lines: list[DivinationLine] = []
    headlines = []
    for card, rev, (pos_en, pos_zh, role) in drawn:
        meaning = card.reversed if rev else card.upright
        text = f"{card.name} {'(reversed)' if rev else '(upright)'} — {meaning}"
        div_lines.append(
            DivinationLine(
                position=f"{pos_en} ({pos_zh}) — {role}",
                text=text,
                is_reversed=rev,
                extra={"card_id": card.id, "image": card.image, "name_zh": card.name_zh},
            )
        )
        if pos_en in ("Present", "Card", "Outcome"):
            headlines.append(card)

    primary_card, *_ = drawn[0]
    primary_rev = drawn[0][1]
    headline_zh = primary_card.name_zh + ("（逆位）" if primary_rev else "")
    headline_en = primary_card.name + (" (reversed)" if primary_rev else "")

    return DivinationResult(
        method="tarot",
        question=question,
        seed=seed,
        headline_zh=headline_zh,
        headline_en=headline_en,
        primary=f"{primary_card.name} ({primary_card.name_zh})",
        secondary=(
            drawn[-1][0].name + " (Outcome)"
            if len(drawn) > 1
            else ""
        ),
        judgment=(primary_card.reversed if primary_rev else primary_card.upright),
        image=primary_card.image,
        lines=div_lines,
        structured={
            "spread": spread,
            "n_cards": str(len(drawn)),
            "primary_card_id": primary_card.id,
            "outcome_card_id": drawn[-1][0].id if len(drawn) > 1 else "",
        },
        raw_state={
            "drawn_card_ids": [c.id for c, _, _ in drawn],
            "reversed_flags": [r for _, r, _ in drawn],
        },
    )
