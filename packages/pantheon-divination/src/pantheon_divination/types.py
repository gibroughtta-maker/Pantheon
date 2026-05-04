"""Common types for divination results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DivinationLine:
    """One row of structured output (a hexagram line, a card position, a rune)."""

    position: str            # "Initial Six (爻一)", "Past", "Knight of Cups", ...
    text: str                # canonical text from the data table
    is_changing: bool = False  # for iching: changing line?
    is_reversed: bool = False  # for tarot: reversed?
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class DivinationResult:
    """Result returned by every cast() function. Structured so the same
    rendering / contextualization code works across methods."""

    method: Literal["iching", "tarot", "runes", "astrology", "ziwei"]
    question: str
    seed: int

    headline_zh: str = ""    # 卦名 / 牌名 / 符文名 / 主星 — short, primary
    headline_en: str = ""

    primary: str = ""        # 卦象 / Major card / Primary rune — single line
    secondary: str = ""      # transformation hexagram / cross card / supporting

    judgment: str = ""       # 卦辞 / card upright meaning / rune symbolism (PD)
    image: str = ""          # 象传 / card image keyword / etc.

    lines: list[DivinationLine] = field(default_factory=list)

    structured: dict[str, str] = field(default_factory=dict)
    raw_state: dict = field(default_factory=dict)

    disclaimer: str = (
        "本结果由占卜插件依据传统符号体系生成。"
        "Not a prediction; not professional advice."
    )

    def short_summary(self) -> str:
        return (
            f"[{self.method}] {self.headline_zh} / {self.headline_en} — "
            f"{self.primary}"
        )


class FormatHelpers:
    """Helpers shared by individual methods."""

    @staticmethod
    def hexagram_unicode(yin_yang: list[int]) -> str:
        """Render 6 lines (top to bottom, 0=yin, 1=yang) as a unicode glyph
        column. Just for display; the canonical numbering is what matters."""
        out = []
        for v in yin_yang:
            out.append("▆▆▆▆▆" if v == 1 else "▆▆ ▆▆")
        return "\n".join(out)
