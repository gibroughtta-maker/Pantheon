# pantheon-pack-founders — Audit Record

This file is the public record of cultural-sensitivity, historical-accuracy,
and bias review for the three personas in this pack. Per the v0.3 plan,
**no version of this pack may be released to PyPI without three reviewers
of distinct standpoint signing off, and the median
`cultural_sensitivity_score` ≥ 0.85.**

## Reviewer panel structure

Each persona requires reviews from **three** distinct standpoints:

1. **Confessional** — a reviewer who self-identifies as a practitioner of
   the tradition (Christian for Jesus, Muslim for Muhammad, Buddhist for
   Buddha).
2. **Academic** — a reviewer trained in the historical-critical study of
   the tradition (e.g. New Testament scholar, early-Islam historian,
   Buddhist studies academic), without confessional commitment to it.
3. **Outside / secular** — a reviewer with no religious commitment to the
   tradition (and ideally one whose own background is from a different
   tradition entirely), to surface unconscious in-group framing.

Each reviewer scores on:

| Axis | Range | Meaning |
|---|---|---|
| `historical_accuracy` | 0–1 | How well does the persona match best contemporary scholarship? |
| `tradition_respect` | 0–1 | Would this be experienced as respectful by a serious practitioner? |
| `stereotype_avoidance` | 0–1 | Does the persona avoid orientalist / caricature framing? |
| `cultural_sensitivity_score` | 0–1 | Composite: median of the three above |

The pack-level score is the **median** of the three reviewers'
composite scores. Released versions must be ≥ 0.85.

## Issue & appeal process

Anyone who believes a quotation is misattributed, a teaching is
caricatured, or a sensitive aspect is mishandled may open an issue on
the `pantheon` repo with the label `pack:founders`. Maintainers commit
to a substantive response within 14 days. Substantive responses look
like one of:

- corpus excerpt linked + acknowledgement that the persona will be
  retuned in the next release;
- corpus excerpt linked + reasoned disagreement;
- referral to the audit panel for re-review.

## Persona records

### Jesus of Nazareth

- **Reviewers:**
  - Confessional: _(unfilled — pre-release)_
  - Academic: _(unfilled — pre-release)_
  - Outside: _(unfilled — pre-release)_
- **cultural_sensitivity_score:** _pending_
- **Status:** ⛔ NOT RELEASED — awaiting first review round.
- **Known biases (declared in persona.yaml):** see `personas/jesus/persona.yaml` `audit.known_biases`.

### Prophet Muhammad

- **Reviewers:**
  - Confessional: _(unfilled — pre-release)_
  - Academic: _(unfilled — pre-release)_
  - Outside: _(unfilled — pre-release)_
- **cultural_sensitivity_score:** _pending_
- **Status:** ⛔ NOT RELEASED — awaiting first review round.
- **Known biases (declared in persona.yaml):** see `personas/muhammad/persona.yaml` `audit.known_biases`.
- **Special note:** the persona's prompt requires that any rendering of
  Quranic text into English or Chinese be marked as "interpretation of
  meaning, not the verse itself". Reviewers should verify this is
  consistently honoured in calibration test runs.

### Siddhartha Gautama (the Buddha)

- **Reviewers:**
  - Confessional: _(unfilled — pre-release)_
  - Academic: _(unfilled — pre-release)_
  - Outside: _(unfilled — pre-release)_
- **cultural_sensitivity_score:** _pending_
- **Status:** ⛔ NOT RELEASED — awaiting first review round.
- **Known biases (declared in persona.yaml):** see `personas/buddha/persona.yaml` `audit.known_biases`.
- **Special note:** the persona is bounded to early canonical text (Pali
  + Chinese Agamas). Reviewers from Mahayana / Vajrayana / Pure Land
  traditions should comment on whether this bounding is acceptable, or
  whether a separate persona pack is warranted for those traditions.

## Re-audit triggers

The pack must be re-audited if any of:

- A persona's `system_prompt` is materially edited.
- The corpus manifest changes the included sources or translators.
- A calibration run produces `cultural_sensitivity_score` movement > 0.10
  on any axis since the last sign-off.
- An accepted community issue (see appeal process) is filed.

## License

This audit record is published under CC-BY-SA 4.0 to encourage external
commentary and republication.
