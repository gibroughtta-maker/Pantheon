# pantheon-divination

Divination methods for the [Pantheon](https://github.com/gibroughtta-maker/Pantheon)
framework. Five methods, opt-in:

- **易经** (Yijing / I Ching) — 64 hexagrams, three-coin method (default)
- **Tarot** — 78 cards, Celtic Cross spread (default)
- **Norse runes** — 24 runes (Elder Futhark), three-rune spread (default)
- **Astrology** — Skyfield-backed real ephemerides (requires `[astrology]` extra)
- **紫微斗数** — Ziwei chart (M4+ — scaffold only for now)

## Strict by design

The framework's central principle: **canonical text — hexagram judgement,
card meaning, rune symbolism — is NEVER LLM-generated.** It comes from a
structured public-domain database. The LLM is used ONLY to contextualize a
result for the specific question the user asked. Each method ships a
`--strict` mode that refuses any LLM contextualization.

## Opt-in & legal

```python
import pantheon_divination as pd

# Step 1: read and accept the disclaimer (raises if region is restricted)
print(pd.DISCLAIMER_TEXT)
pd.accept_disclaimer()

# Step 2: use any method
result = pd.iching.cast(question="Should I take the buyout?", seed=42)
print(result.headline_zh)   # 卦名 + 卦辞
print(result.headline_en)
for line in result.lines:
    print(line.position, line.is_changing, line.text)

result = pd.tarot.cast(question="...", spread="celtic_cross", seed=42)

# Step 3: optionally let the LLM contextualize the result for the question
contextualized = await pd.contextualize(result, judge=my_model)
```

`PANTHEON_REGION=cn` will refuse to load (per plan §9.2). Set
`PANTHEON_DIVINATION_REGION_OVERRIDE=1` to override at your own risk.

## Verdict disclaimer

Every divination result carries an automatic disclaimer saying that the
output is based on the traditional symbolic system, not predictive
science, and is not advice for medical, legal, or financial decisions.

## License

Apache-2.0 code; CC-BY-SA 4.0 data files.
