# Founders pack — Calibration runbook

This runbook walks through producing real, defensible skill scores for
the three founder personas (jesus / muhammad / buddha). It is the
process maintainers must follow before flipping the pack from "alpha,
hand-filled placeholders" to "calibrated, audited, releasable".

The pack ships with all skills at `0.50` placeholder. **Do not remove
the placeholder warning from `audit.calibration.method = hand_filled`
until this runbook has been completed end-to-end.**

## Step 0 — Prerequisites

```bash
pip install -e packages/pantheon-core
pip install -e packages/pantheon-pack-founders

# For real semantic embedding (recommended):
pip install pantheon-debate[calibration]   # sentence-transformers, ~100MB

# For real LLM judges (recommended for L4):
export PANTHEON_GATEWAY=openclaw
export OPENCLAW_BASE_URL=...
export OPENCLAW_API_KEY=...
```

The anchor personas (confucius / socrates / naval) must be calibrated
**first**; their hand-filled scores are not trustworthy as anchors.
Plan order:

```bash
pantheon corpus fetch confucius socrates naval
pantheon persona calibrate confucius socrates naval \
    --gateway openclaw \
    --judges claude-opus-4-7,gpt-4o,deepseek-chat
```

Resolve any σ-flagged dimensions in `manual_review/<persona>.md` before
proceeding.

## Step 1 — Fetch canonical corpora

```bash
# Accept the disclaimer:
python -c "import pantheon_pack_founders as ppf; ppf.accept_disclaimer()"

# Fetch all sources listed in each persona's corpus/manifest.yaml:
pantheon corpus fetch jesus muhammad buddha

# Verify sha256 of cached files (fills the empty sha256 entries on
# first successful fetch; future runs verify against them):
pantheon corpus verify jesus muhammad buddha
```

By default corpus lands at `~/.pantheon/corpus/<persona>/`. If you are
in a region or behind a network policy that blocks any of the upstream
hosts, supply `--mirror <prefix>` to redirect.

## Step 2 — Run calibration

```bash
pantheon persona calibrate jesus muhammad buddha \
    --anchors confucius,socrates,naval \
    --judges claude-opus-4-7,gpt-4o,deepseek-chat \
    --gateway openclaw \
    --seed 0 \
    --write-back
```

This produces:

- `~/.pantheon/calibration/<run_id>.jsonl` — the recorded run
- Updated `personas/<id>/persona.yaml` — `skills:` overwritten with
  fused L2+L4 scores, `audit.calibration` block populated
- `manual_review/<id>.md` — for any dimension where |L2 − L4| > 0.2

Expected duration: ≈ 7 dims × 6 probes × 3 anchors × 3 judges = 378
LLM calls per founder, ~10 minutes per founder over a fast gateway.

## Step 3 — Resolve manual review

For each dimension flagged in `manual_review/<persona>.md`:

1. Read both L2 (corpus retrieval coverage) and L4 (pairwise vs anchors)
   scores
2. Inspect the recorded JSONL to see which probes drove the disagreement
3. Decide a final value with explicit rationale
4. Write the decision into `audit.calibration.manual_overrides[<dim>]`:
   ```yaml
   audit:
     calibration:
       manual_overrides:
         divination:
           value: 0.30
           reason: "L2/L4 disagreed; reviewer panel adjudicated to 0.30 — the persona's tradition records prophetic experience, but does not endorse divination practice as commonly understood by the framework's probe."
   ```
5. Re-run calibration with `--write-back` to apply the override

## Step 4 — Audit panel

For each persona, recruit three reviewers per `AUDIT.md`:

- One self-identifying practitioner of the tradition
- One academic (historical-critical study, no confessional commitment)
- One outsider (no commitment to the tradition, ideally from a
  different tradition)

Each scores on `historical_accuracy` / `tradition_respect` /
`stereotype_avoidance`. The composite is the median; the persona-level
`cultural_sensitivity_score` is the median of the three reviewers'
composites.

Record names + scores in `AUDIT.md`. **Do not release a version where
any persona has score < 0.85.** Update the status from "⛔ NOT RELEASED"
to "✓ released v0.1.0" in `AUDIT.md` when ready.

## Step 5 — Re-audit triggers

Re-run this runbook from Step 1 when any of:

- A persona's `system_prompt` is materially edited
- The corpus manifest changes the included sources
- A calibration run shifts any axis by > 0.10 since last sign-off
- An accepted community issue (per AUDIT.md SOP) is filed against
  this persona

## Dry-run / CI verification

The framework includes a **dry-run** test that exercises this path
end-to-end with mocked judges and a tiny synthetic corpus, so the
pipeline can be verified in CI without API access:

```bash
pytest packages/pantheon-pack-founders/tests/test_calibration_dryrun.py
```

The dry-run does not produce defensible scores — it only proves the
machinery wires up correctly.
