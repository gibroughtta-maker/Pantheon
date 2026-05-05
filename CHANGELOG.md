# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `Session.resume()` lets a debate continue after `BudgetExceeded` with a
  fresh budget instead of being permanently terminated.
- Oracle `render_verdict` failure is now caught and produces a rule-based
  `degraded_verdict` instead of dropping the debate entirely.
- 5 failure-mode injection tests exercise the documented degrade paths
  (gateway 429 / persona timeout / gateway down / oracle fail / corpus fail).
- Golden-debates fixture infrastructure under `golden_debates/`; runs from
  scripted MockGateway replies for deterministic CI, with an opt-in
  `--use-real-llm` flag for live verification.
- `pantheon-pack-template` cookiecutter scaffold for community persona
  packs (entry-point + persona.yaml skeleton + AUDIT.md template).
- Chinese-language docs site translated (was previously English stubs).
- `py.typed` marker in every distributed package.
- LICENSE files (MIT for code; Apache-2.0 + CC-BY-SA 4.0 for the founders
  pack) and a top-level CHANGELOG.

### Changed
- (unreleased changes here)

## [0.1.0a0] — 2026-05-04 (alpha milestone — not on PyPI)

### Added
- M0 Spike: four-layer architecture (Agent / Persona / Model / Memory),
  five-phase FSM debate engine, queue-based swap semantics with auto
  handoff statements, JSONL replay with deterministic `debate_id`,
  `BudgetGuard`, three built-in personas (confucius / socrates / naval),
  55 tests passing.
- M1.5 Skill calibration: probes (7 dims × 6 questions),
  `EmbeddedCorpusStore` (in-memory hybrid embedding + BM25),
  `HashEmbedder` dependency-free fallback,
  L2 retrieval scorer + L4 pairwise (Bradley-Terry) scorer + runner with
  σ flagging for manual review,
  CLI `persona calibrate` / `calibration replay` / `corpus fetch` / `corpus verify`.
- M1.5 Founders pack (`pantheon-pack-founders`): jesus / muhammad / buddha
  with `accept_disclaimer()` + `PANTHEON_REGION=cn` refusal + AUDIT.md
  + corpus-fetch-on-demand manifests (no scripture in repo).
- M1 Production core: Auditor wired to real corpus retrieval,
  Devil's Advocate auto-summon (real spawn, single-turn challenger),
  `RateLimiter` (token-bucket per-model RPM/TPM),
  `OpenClawGateway` + `NimGateway` adapters,
  `SqliteEpisodicStore`.
- M2 MCP server (`pantheon-mcp`): stdio MCP server exposing 8 tools
  (summon / debate / swap_persona / swap_model / get_verdict /
  cast_divination / list_personas / audit_persona).
- M2 personas (10 new, total 13): laozi, mencius, plato, aristotle,
  marcus_aurelius, nietzsche, einstein, jobs, paul_graham, charlie_munger.
- M2 OpenClaw skill manifest (`@openclaw/skill-pantheon`).
- M2 docs site scaffold (MkDocs + i18n; en + zh).
- M3 Persona pack SDK: `pantheon.personas` entry-point auto-discovery,
  `registry.has()` / `rescan_entry_points()` helpers.
- M3 `TopicClassifier` — three-strategy fusion (tags + embedding + optional LLM).
- M3 `bench/models.yaml` seed (7 models, 7 skill dims + cultural_depth).
- M3 `compute_weights` wired to topic-weighted model capability + corpus_coverage.
- M3 CLI `pantheon pack audit` + `pack info`.
- M4 `pantheon-divination`: iching (64 hexagrams, three-coin), tarot
  (78 cards, 3 spreads), Elder Futhark runes (24, 3 spreads), Skyfield
  astrology (`[astrology]` extra), ziwei stub. `accept_disclaimer()` gate.
- M4 `pantheon-bridges`: `EventSink` Protocol + `pipe()` helper +
  ObsidianSink / TelegramSink / DiscordSink with per-sink failure isolation.
- M4 MCP `cast_divination` wired to pantheon-divination.

### Test count
175 tests passing across 5 distributable packages.
