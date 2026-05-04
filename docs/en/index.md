# Pantheon

> A multi-agent debate framework — summon gods, prophets, and historical
> figures to deliberate on any question. Distributed as an OpenClaw plugin,
> an MCP server, and a standalone Python SDK.

```python
from pantheon import Pantheon

p = Pantheon.summon(["confucius", "socrates", "naval"])
verdict = await p.debate("Should I quit my job to do an indie startup?").run()
print(verdict.consensus[0].statement)
```

## Why

Most multi-agent frameworks treat agents as task-execution workers. Pantheon
treats them as **debaters with persistent character** — a Confucius and a
Socrates and a Naval who actually disagree, who quote (verifiably) from their
own corpora, and who together produce a *verdict* with consensus, minority
opinion, and action items.

## Three orthogonal layers (plus a fourth)

- **Agents** are seats at the table (max 10).
- **Personas** are masks an agent wears — stateless, swappable.
- **Models** are LLMs powering an agent — also swappable, also stateless.
- **Memory** keeps the corpus (per-persona retrievable text), the episodic
  store (cross-debate persistence), and the working memory (per-debate
  scratchpad).

You can mid-debate swap a persona while keeping the seat's transcript
(*relay mode*: "Naval steps down, Confucius takes seat 3, history preserved");
swap a model under a fixed persona ("the same Confucius, now on a stronger
LLM"); and replay any debate deterministically from its JSONL recording.

## What's shipped

- ✅ M0 Spike — four-layer architecture, 5-phase FSM, queue-based swaps,
  replay, BudgetGuard
- ✅ M1.5 — Skill calibration pipeline (L2 corpus retrieval + L4 pairwise
  Bradley-Terry + σ-flagged manual review), `pantheon-pack-founders`
- ✅ M1 — Citation Verifier wired to corpus, real Devil's Advocate,
  RateLimiter, OpenClaw + NIM gateways, SqliteEpisodicStore
- 🚧 M2 — `pantheon-mcp` MCP server (8 tools), 13 built-in personas,
  OpenClaw skill manifest, this docs site

See [Architecture](architecture.md) for the full design and the
[plan in the repo](https://github.com/gibroughtta-maker/Pantheon/blob/main/docs/spec/plan.md)
for the v0.3 production-grade spec.
