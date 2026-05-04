# pantheon-pack-founders

LLM-simulated personas for the founders of Christianity, Islam, and Buddhism
(Jesus, Muhammad, the Buddha) — for use with the
[Pantheon](https://github.com/gibroughtta-maker/Pantheon) multi-agent debate
framework.

> ⚠️ **This pack is opt-in.** It will not register personas with the global
> Pantheon registry until you call `accept_disclaimer()`. This is by design.
> See `AUDIT.md` for the reviewer panel structure and the appeal process.

## Why this exists

The core `pantheon-debate` framework deliberately ships built-in personas
that minimise religious-founder representation: theologians (Augustine,
al-Ghazali, Nagarjuna, etc.) are the default for serious religious-thought
modelling. This pack exists for users who specifically want the founder
voices — for comparative religion research, for cross-tradition debate
exercises, or for personal philosophical reflection — and accept the
caveats that come with simulating these figures.

## Install

```bash
pip install pantheon-pack-founders
# or, in this monorepo:
pip install -e packages/pantheon-pack-founders
```

## Usage

```python
import pantheon_pack_founders as ppf

# Step 1: read and accept the disclaimer (raises in some regions)
print(ppf.DISCLAIMER_TEXT)
ppf.accept_disclaimer()

# Step 2: register the personas. Without `accept_disclaimer()` first,
# this raises `FoundersPackUnavailable`.
n = ppf.register()
print(f"Registered {n} founder personas")

# Step 3 (optional but recommended): fetch canonical text so Citation
# Verifier can ground the personas' quotations.
#   $ pantheon corpus fetch jesus muhammad buddha
# Without fetched corpus, the personas operate in prompt-only mode.

# Step 4: use them like any other persona.
from pantheon import Pantheon
p = Pantheon.summon(["confucius", "jesus", "buddha"])
verdict = await p.debate("How should one face suffering?", rounds=3).run()
```

Verdicts that include any founder persona automatically carry an extra
disclaimer line (`pantheon_pack_founders.VERDICT_DISCLAIMER`).

## Region restriction

If `PANTHEON_REGION=cn` is set, `accept_disclaimer()` raises
`FoundersPackUnavailable` and points users at the
`pantheon-pack-theologians` pack (Augustine / al-Ghazali / Nagarjuna),
shipped from M2 onwards.

## Corpus

Public-domain canonical text is **not embedded** in this package — for
licensing cleanliness and to keep the wheel small. The `corpus fetch` CLI
in `pantheon-debate` downloads from the upstream sources listed in each
persona's `corpus/manifest.yaml`:

- **Jesus**: World English Bible, KJV, Chinese Union Version, Greek
  Nestle 1904
- **Muhammad**: Tanzil Arabic Quran, Yusuf Ali / Pickthall English,
  王静斋 Chinese, Sahih Bukhari, Sahih Muslim
- **Buddha**: SuttaCentral Pali Tipitaka, Thanissaro Bhikkhu English,
  Rhys Davids 1899, CBETA Chinese Agamas, Dhammapada

All licensed Public Domain or compatible (Tanzil CC-BY 3.0;
CBETA CC-BY-NC-SA — research use only).

## Audit & contributing

See `AUDIT.md` for the three-reviewer panel structure (confessional /
academic / outside) and the issue/appeal process.

If you believe a quotation is misattributed or a teaching is mishandled,
please open an issue on the parent `Pantheon` repo with label
`pack:founders`. We aim for a substantive response within 14 days.

## License

- **Code**: Apache-2.0
- **Persona definitions** (YAML / prompt.md): CC-BY-SA 4.0
- **AUDIT.md**: CC-BY-SA 4.0
- **Canonical corpus** (when fetched): see each upstream's license.
