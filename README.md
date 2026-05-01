# Pantheon (万神殿)

> A multi-agent debate framework — summon gods, prophets, and historical figures
> to deliberate on any question. Distributed as an OpenClaw plugin, an MCP
> server, and a standalone Python SDK.

```python
from pantheon import Pantheon

p = Pantheon.summon(["confucius", "socrates", "naval"])
verdict = await p.debate("Should I quit my job to do an indie startup?").run()
print(verdict.consensus[0].statement)
```

## Architecture

Four orthogonal layers (see [`/root/.claude/plans/pantheon-vectorized-quiche.md`](../../root/.claude/plans/pantheon-vectorized-quiche.md) for the v0.3 design doc):

| Layer | Role |
|---|---|
| **Agent** (max 10) | Debate seat, persistent history |
| **Persona** | Stateless mask worn by an agent |
| **Model** | Stateless LLM engine |
| **Memory** | Corpus / Episodic / Working stores |

Plus: 5-phase FSM debate engine (opening → cross_exam → rebuttal → synthesis* → verdict),
queue-based swap semantics, replay determinism, BudgetGuard, citation verifier.

## Status

**M0 spike — architecture verified.** This commit lays the four-layer foundation,
the FSM, queue-based swaps with handoff statements, JSONL replay, and 3 built-in
personas. All 55 tests pass against `MockGateway`.

What's next (M1):
- Real LLM gateways (`OpenClaw`, `NIM`, OpenAI-compat all already supported as classes)
- Citation Verifier with corpus retrieval (sqlite-vec)
- Devil's Advocate auto-summon
- `pantheon-mcp` MCP server packaging
- 12–15 high-quality personas with `pantheon pack audit` clean

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e packages/pantheon-core
python examples/01_quickstart.py
```

Or via CLI:

```bash
pantheon list-personas
pantheon debate confucius socrates naval -q "Should I take the buyout?"
pantheon replay <debate_id>
```

## Repository

```
pantheon/
├── packages/pantheon-core/         # the SDK
│   ├── src/pantheon/
│   │   ├── core/      agent, persona, model, pantheon, weights, relay
│   │   ├── memory/    working, corpus, episodic
│   │   ├── gateway/   base, mock, openai_compat, replay
│   │   ├── debate/    fsm, phases, session
│   │   ├── roles/     moderator, oracle, auditor
│   │   ├── obs/       budget, replay (recorder), otel
│   │   ├── types/     persona spec, verdict, events
│   │   └── cli.py
│   ├── personas/      built-in pack: confucius, socrates, naval
│   └── tests/         55 tests, all passing
├── examples/          quickstart, streaming, relay, model_swap, replay
└── /root/.claude/plans/pantheon-vectorized-quiche.md   # v0.3 plan
```

## License

MIT (core) · Apache 2.0 (plugin SDK) · CC-BY-SA 4.0 (persona corpus).
