# Architecture

## Four orthogonal layers

```
Agent  (seat / persistent transcript)
  ↓ wears
Persona (stateless mask)
  ↓ powered by
Model  (stateless LLM engine)
  ↓ grounded in
Memory (corpus + episodic + working)
```

Each layer is swappable independently. This is the framework's signature
property.

| Operation | Changes | Preserves |
|---|---|---|
| `agent.swap_persona(p)` | persona, system prompt, corpus, citation style | history, seat, model |
| `agent.swap_model(m)` | LLM, provider | persona, history, corpus |
| `agent.swap_memory(profile)` | episodic view | persona, model, history |

Swaps are queued via the Pantheon coordinator and applied at phase
boundaries — never mid-phase. This eliminates race conditions in
streaming debates.

## Five-phase FSM

```
CREATED → OPENING → CROSS_EXAM → REBUTTAL → SYNTHESIS* → VERDICT → CLOSED
                                              (loop ≤ 3)
```

Each phase is a pluggable `PhaseStrategy`. The Moderator detects soft
consensus during synthesis and summons the Devil's Advocate — a single-
turn challenger that names what the consensus skipped.

## Citation grounding

Every direct quote a persona produces is checked against that persona's
corpus by the Auditor. Verified quotes count for full grounding;
fabricated quotes are surfaced in the Verdict's `quality.unverified_quote_count`.

## Skill calibration

Skill scores are not hand-filled. The calibration pipeline runs:

- **L2** — for each of 7 dimensions × 6 prototype questions, retrieve from
  corpus and score coverage
- **L4** — pairwise LLM-judge tournament against anchor personas, resolved
  via Bradley-Terry MLE
- **Fusion** — weighted mean; |L2 − L4| > 0.2 flags the dimension for
  manual review (not silent averaging)

See [Calibration](calibration.md) for details.

## Production-grade primitives

- **OpenTelemetry** — every phase / call / retrieval is a span
- **Replay** — JSONL recording per debate; `ReplayGateway` makes any
  debate reproducible at zero cost
- **BudgetGuard** — pre-call quotas; never silent
- **RateLimiter** — token-bucket per model; blocks rather than raises
- **5 failure-mode degrade paths** — single persona timeout, gateway
  429, gateway down, oracle fail, corpus retrieval fail

See the [v0.3 plan](https://github.com/gibroughtta-maker/Pantheon/blob/main/docs/spec/plan.md)
for the full spec.
