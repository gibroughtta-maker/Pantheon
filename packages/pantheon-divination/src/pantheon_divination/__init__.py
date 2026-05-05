"""Pantheon divination — opt-in package.

Per plan §9.2 + §11, divination is shipped as an independent package that
must be explicitly imported and accepted before any method can be used.
The accept_disclaimer() call also enforces the region restriction
(PANTHEON_REGION=cn refuses).

Public API:
  pd.accept_disclaimer()
  pd.iching.cast(question, seed)         → DivinationResult
  pd.tarot.cast(question, spread, seed)  → DivinationResult
  pd.runes.cast(question, seed)          → DivinationResult
  pd.astrology.cast(question, time)      → DivinationResult  (requires `[astrology]` extra)
  pd.ziwei.cast(question, birth)         → DivinationResult  (M4+; stub)
  await pd.contextualize(result, judge)  → str  (LLM contextualization, optional)
"""
from __future__ import annotations

import os

from pantheon_divination.types import DivinationLine, DivinationResult, FormatHelpers

_DISCLAIMER_ACCEPTED = False

DISCLAIMER_TEXT = """\
Pantheon divination is a research and exploration tool. Each method is
implemented faithfully to its traditional symbolic system (易经 trigrams,
Rider–Waite tarot, Elder Futhark, real astronomical positions for
astrology, 紫微 chart algorithms for ziwei).

The output is the symbolic system's interpretation. It is NOT:
  • a prediction in any scientific sense
  • a substitute for medical, legal, financial, or psychological advice
  • a substitute for human judgement on important life decisions

Each result is generated deterministically from your question + seed +
the public-domain data tables that ship with this package. The LLM
contextualization step (optional) is constrained to interpret the
fixed result, never to invent fresh oracular text.

By calling accept_disclaimer() you acknowledge:
  • You understand divination output is not a prediction
  • You will not represent the output to others as a prediction
  • You will not use the output to coerce, defraud, or deceive others
  • In some jurisdictions, divination is regulated; you are responsible
    for compliance in your own jurisdiction
"""


class DivinationUnavailable(RuntimeError):
    """Raised when the package cannot be loaded for region/policy reasons."""


def accept_disclaimer() -> None:
    """Acknowledge the disclaimer; check region restriction."""
    global _DISCLAIMER_ACCEPTED
    region = os.environ.get("PANTHEON_REGION", "").strip().lower()
    override = os.environ.get("PANTHEON_DIVINATION_REGION_OVERRIDE", "").strip()
    if region == "cn" and override != "1":
        raise DivinationUnavailable(
            "pantheon-divination refuses to load in region=cn. "
            "Set PANTHEON_DIVINATION_REGION_OVERRIDE=1 to override "
            "at your own risk and responsibility for local compliance."
        )
    _DISCLAIMER_ACCEPTED = True


def _ensure_accepted() -> None:
    if not _DISCLAIMER_ACCEPTED:
        raise DivinationUnavailable(
            "Call pantheon_divination.accept_disclaimer() before using any "
            "divination method. Disclaimer text:\n\n" + DISCLAIMER_TEXT
        )


# Method modules import lazily so importing the package itself is cheap.
# Submodules call _ensure_accepted() before doing any real work.

from pantheon_divination import astrology, iching, runes, tarot, ziwei  # noqa: E402
from pantheon_divination.contextualize import contextualize  # noqa: E402

VERDICT_DISCLAIMER = (
    "本结果由占卜插件依据传统符号体系生成，不是预测，亦不构成医疗、法律、"
    "财务或心理健康建议。\n"
    "This result is produced by the divination plugin per a traditional "
    "symbolic system. It is not a prediction; not advice."
)

__version__ = "0.1.0a0"
__all__ = [
    "DISCLAIMER_TEXT",
    "DivinationLine",
    "DivinationResult",
    "DivinationUnavailable",
    "FormatHelpers",
    "VERDICT_DISCLAIMER",
    "accept_disclaimer",
    "astrology",
    "contextualize",
    "iching",
    "runes",
    "tarot",
    "ziwei",
]
