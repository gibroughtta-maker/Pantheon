# Golden debates

Reference debates that should produce stable verdicts under a fixed
gateway + seed. They serve two purposes:

1. **CI regression** — every PR runs them with the deterministic
   `MockGateway` against the recorded `expected.json` to catch any
   accidental change in the FSM, weight composition, or verdict shape.
2. **Quality eyeballing** — opt-in `pantheon golden run --use-real-llm`
   re-runs them against a real gateway (OpenClaw / OpenAI / NIM) and
   diffs the verdict shape (not the prose) for human review.

## Layout

```
golden_debates/
├── README.md
├── 01_indie_startup.yaml      # career / business / risk
├── 02_face_grief.yaml         # emotion / ethics
└── 03_reform_or_revolution.yaml   # governance / ethics
```

Each file is a self-contained spec:

```yaml
id: gd_001
question: "Should I quit my job to start an indie startup?"
agents:
  - { seat: 1, persona: confucius, model: deepseek-chat }
  - { seat: 2, persona: socrates,  model: claude-opus-4-7 }
  - { seat: 3, persona: naval,     model: claude-opus-4-7 }
rounds: 3
seed: 42
expected:
  schema_version: "1.0"
  must_address: [risk, opportunity_cost, family_obligation]
  must_not_contain_substring: ["lorem ipsum"]
  rubric_thresholds:
    reasoning_quality: 0.75
    citation_accuracy: 0.85
    cultural_consistency: 0.80
```

## Run

```bash
# Mock gateway (deterministic, free):
pantheon golden run

# Real LLM (requires API access):
PANTHEON_GATEWAY=openclaw OPENCLAW_API_KEY=... \
  pantheon golden run --use-real-llm

# Run only one:
pantheon golden run 01_indie_startup
```

## Acceptance criteria

For CI, a debate passes if:

- It completes without raising
- The Verdict has at least one consensus point OR `no_consensus=True`
- `quality.unverified_quote_count == 0` for the deterministic mock
  (the mock doesn't produce direct quotations)
- The `expected.must_address` topics each appear at least once across
  the speech transcripts when run with a real LLM (this is `--use-real-llm`
  only — the mock doesn't produce substantive content)

The thresholds in `rubric_thresholds` are evaluated by an LLM judge
when running with `--use-real-llm` (see plan §13.2).
