"""LLM contextualization of a fixed divination result.

Per plan §11: the canonical text — judgements, card meanings, rune
symbolism — is NEVER LLM-generated. The LLM is allowed to interpret a
FIXED result for the user's specific question.

In `--strict` mode this function is bypassed and the structured result
is returned verbatim. Otherwise the LLM is invited to write 2-3
paragraphs that:

  1. Acknowledge the question
  2. Walk through what the symbolic system says (using the canonical
     keywords already in the result)
  3. Surface the tension or invitation those keywords name

The LLM is explicitly forbidden from introducing new oracular text,
inventing details about the cards/hexagram/runes that are not in the
result, or making confident predictions.
"""
from __future__ import annotations

from pantheon_divination.types import DivinationResult


_PROMPT = """\
You are interpreting a divination result for a user. The canonical
output is fixed; do NOT invent oracular text, do NOT add card or
hexagram meanings beyond what is given. Your job is to relate the
fixed symbolic output to the user's specific question in 2-3 short
paragraphs.

You must:
  - Begin with one sentence acknowledging the question.
  - Walk through the symbolic output position by position, in order,
    using ONLY the keywords given.
  - Close with the tension or invitation the symbols suggest — never
    a confident prediction.

You must NOT:
  - Invent additional symbols, cards, or hexagram lines
  - Quote canonical judgement text not given to you
  - Frame the result as a prediction
  - Recommend specific medical, legal, or financial actions

Result follows.
"""


async def contextualize(
    result: DivinationResult,
    judge,                       # pantheon.core.model.Model
    *,
    strict: bool = False,
) -> str:
    """Return a contextualized interpretation. If `strict`, just
    formats the structured result as text and skips the LLM."""
    if strict or judge is None:
        return _strict_render(result)

    user_block = _strict_render(result)
    messages = [
        {"role": "system", "content": _PROMPT},
        {"role": "user", "content": user_block},
    ]
    try:
        out = await judge.call(messages, temperature=0.5, max_tokens=600)
        return out.text + "\n\n---\n" + result.disclaimer
    except Exception as e:  # noqa: BLE001 — LLM failure → strict fallback
        return _strict_render(result) + f"\n\n[contextualization unavailable: {e}]"


def _strict_render(result: DivinationResult) -> str:
    lines = [
        f"Method: {result.method}",
        f"Question: {result.question}",
        f"Seed: {result.seed}",
        "",
        f"Headline: {result.headline_zh} / {result.headline_en}",
        f"Primary: {result.primary}",
    ]
    if result.secondary:
        lines.append(f"Secondary: {result.secondary}")
    if result.judgment:
        lines.append(f"Judgment: {result.judgment}")
    if result.image:
        lines.append(f"Image: {result.image}")
    if result.lines:
        lines.append("")
        lines.append("Positions:")
        for line in result.lines:
            tag = []
            if line.is_changing:
                tag.append("changing")
            if line.is_reversed:
                tag.append("reversed")
            tag_str = f" [{', '.join(tag)}]" if tag else ""
            lines.append(f"  - {line.position}{tag_str}: {line.text}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)
