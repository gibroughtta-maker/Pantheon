# Reference

## Persona YAML schema (v1.0)

See [`pantheon.types.persona.PersonaSpec`](https://github.com/gibroughtta-maker/Pantheon/blob/main/packages/pantheon-core/src/pantheon/types/persona.py).
Concrete examples live in
[`packages/pantheon-core/personas/`](https://github.com/gibroughtta-maker/Pantheon/tree/main/packages/pantheon-core/personas).

## Verdict schema (v1.0)

See [`pantheon.types.verdict.Verdict`](https://github.com/gibroughtta-maker/Pantheon/blob/main/packages/pantheon-core/src/pantheon/types/verdict.py).
Every field validated by Pydantic; `verdict.no_consensus=True` is a
first-class outcome (the framework will not strain to produce a
fake consensus).

## Streaming events

| Event | Fields |
|---|---|
| `SpeechEvent` | seat, persona_id, phase, text, model_id |
| `PhaseBoundaryEvent` | from_phase, to_phase |
| `SwapEvent` | seat, kind (persona/model/memory), from_id, to_id, handoff_statement |
| `SystemEvent` | role (moderator/oracle/auditor/framework), message |
| `VerdictEvent` | debate_id |

All events carry `session_id` and a monotonic `seq`.

## Gateways

| Gateway | When to use |
|---|---|
| `MockGateway` | Tests, demos, replay fallback |
| `ReplayGateway` | Reproduce a recorded debate at zero cost |
| `OpenAICompatibleGateway` | Generic; OpenAI / DeepSeek / vLLM / etc. |
| `OpenClawGateway` | OpenClaw multi-LLM router |
| `NimGateway` | NVIDIA NIM endpoints |

## Memory

| Store | Backend | Lifetime |
|---|---|---|
| `EmbeddedCorpusStore` | in-memory hybrid embedding + BM25 | Process |
| `NullCorpusStore` | none | n/a |
| `SqliteEpisodicStore` | SQLite | Permanent (clearable) |
| `NullEpisodicStore` | none | n/a |
| `WorkingMemory` | in-process | One debate |

## Roles (system agents — never seated)

- `Moderator` — phase shepherd; soft-consensus detection
- `Oracle` — final verdict synthesis (M0 heuristic; M1+ adds LLM pass)
- `Auditor` — claim grounding via corpus retrieval
- `DevilsAdvocate` — single-turn challenger when consensus detected

## Plan reference

The full v0.3 production-grade plan with status markers is at
[`docs/spec/plan.md`](https://github.com/gibroughtta-maker/Pantheon/blob/main/docs/spec/plan.md).
