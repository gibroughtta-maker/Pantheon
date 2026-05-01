# pantheon-debate

Core SDK for the Pantheon multi-agent debate framework. See repository root README and `/root/.claude/plans/pantheon-vectorized-quiche.md` for the full design.

This package provides the four-layer architecture:

- **Agent** — debate seat (max 10 per Pantheon)
- **Persona** — stateless mask worn by an agent
- **Model** — stateless LLM engine
- **Memory** — Corpus / Episodic / Working stores

Plus the 5-phase FSM debate engine, queue-based swap semantics, replay,
budget guard, and MockGateway for deterministic tests.
