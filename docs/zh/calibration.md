# Calibration

Skill scores are not hand-filled. The framework runs a hybrid
**L2 + L4** pipeline that lets every number trace back to a
calibration run.

## L2 — corpus retrieval coverage

For each (persona, dimension) pair the runner takes 6 prototype
questions for that dimension and runs them against the persona's
corpus via `EmbeddedCorpusStore`. The score is mean of top-hit
similarities, weighted by source diversity.

Personas without corpus get `L2 = 0` on every dimension — the framework
correctly says "this corpus does not cover this dimension".

## L4 — pairwise vs anchors

For each dimension the target persona is paired against every anchor
across all probes. Three judges (configurable LLMs) cast votes
(A wins / B wins / tie). Votes are turned into latent strengths via
**Bradley-Terry** maximum likelihood (Zermelo iteration, 30 lines of
pure Python). Strengths are linearly mapped onto the [0, 1] interval
defined by the anchors' known scores.

## Fusion + manual review

```
final = w_l2 · L2  +  w_l4 · L4         (defaults 0.4, 0.6)
σ     = |L2 − L4|
flag  = σ > 0.2  →  manual_review/<persona>.md
```

When L2 and L4 disagree by more than the threshold, the framework does
NOT silently average — it flags the dimension and writes a markdown
stub for a human to resolve. The decision is recorded in
`audit.calibration.manual_overrides`.

## Run it

```bash
# L2-only (no LLM cost):
pantheon persona calibrate confucius --gateway mock --no-write-back

# Full hybrid (real judges):
pantheon persona calibrate jesus muhammad buddha \
  --anchors confucius,socrates,naval \
  --judges claude-opus-4-7,gpt-4o,deepseek-chat \
  --gateway openclaw

# Replay a recorded run (zero cost):
pantheon calibration replay <run_id>
```

Every calibration run lands at `~/.pantheon/calibration/<run_id>.jsonl`.
Same seed + same scripted gateway → byte-identical results.
