"""Persona — runtime wrapper around `PersonaSpec` plus its corpus binding.

Loaded from YAML via `load_persona(path)` or `load_personas_dir(dir)`.
A simple in-memory `registry` lets `Pantheon.summon([id, ...])` resolve ids.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from pantheon.memory.corpus import CorpusStore, NullCorpusStore
from pantheon.memory.embedded_corpus import (
    Embedder,
    EmbeddedCorpusStore,
    HashEmbedder,
    load_corpus_for_persona,
)
from pantheon.types.persona import PersonaSpec


@dataclass
class Persona:
    """Stateless runtime persona = spec + corpus binding."""

    spec: PersonaSpec
    corpus: CorpusStore

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def display_name(self) -> str:
        return self.spec.display.zh or self.spec.display.en or self.spec.id

    def system_prompt(self, *, instance_suffix: str = "") -> str:
        """Render the system prompt for an LLM call. The `[persona:{id}]`
        marker lets the MockGateway route scripted replies; real gateways
        ignore it."""
        sp = self.spec.system_prompt.strip()
        suffix = f"#{instance_suffix}" if instance_suffix else ""
        return f"[persona:{self.spec.id}{suffix}]\n{sp}"


def _resolve_prompt(spec_dir: Path, raw: dict) -> str:
    if "system_prompt" in raw and raw["system_prompt"]:
        return raw["system_prompt"]
    pf = raw.get("system_prompt_file")
    if pf:
        return (spec_dir / pf).read_text(encoding="utf-8")
    return ""


def load_persona(
    path: str | Path,
    *,
    embedder: Embedder | None = None,
) -> Persona:
    """Load a single persona from a YAML file. The system prompt may live in
    a sibling file referenced by `system_prompt_file`. If the persona's
    corpus directory exists and contains files, an `EmbeddedCorpusStore` is
    built; otherwise a `NullCorpusStore` is used.

    `embedder` defaults to `HashEmbedder` (deterministic, no deps) at load
    time so simply importing personas never blocks on a model download.
    Calibration code can swap in a real embedder explicitly.
    """
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    raw["system_prompt"] = _resolve_prompt(p.parent, raw)
    spec = PersonaSpec.model_validate(raw)

    corpus_dir = p.parent / "corpus"
    corpus: CorpusStore
    if corpus_dir.exists() and any(corpus_dir.iterdir()):
        corpus = load_corpus_for_persona(
            spec.id, corpus_dir, embedder=embedder or HashEmbedder()
        )
    else:
        corpus = NullCorpusStore(persona_id=spec.id)
    return Persona(spec=spec, corpus=corpus)


def load_personas_dir(directory: str | Path) -> list[Persona]:
    """Load every `persona.yaml` under `directory` (recursive)."""
    out: list[Persona] = []
    for pyaml in Path(directory).rglob("persona.yaml"):
        out.append(load_persona(pyaml))
    return out


class _Registry:
    """In-memory persona registry. Built-in personas auto-register on import."""

    def __init__(self) -> None:
        self._personas: dict[str, Persona] = {}

    def register(self, persona: Persona) -> None:
        self._personas[persona.id] = persona

    def register_dir(self, directory: str | Path) -> int:
        before = len(self._personas)
        for p in load_personas_dir(directory):
            self.register(p)
        return len(self._personas) - before

    def get(self, persona_id: str) -> Persona:
        if persona_id not in self._personas:
            raise KeyError(
                f"persona {persona_id!r} not registered. "
                f"Available: {sorted(self._personas)[:20]}"
            )
        return self._personas[persona_id]

    def all(self) -> list[Persona]:
        return list(self._personas.values())


registry = _Registry()


# Auto-register built-in personas if they're shipped with the wheel.
def _autoload_builtins() -> None:
    # Installed location (wheel ships personas under pantheon/personas/_builtin/).
    installed = Path(__file__).parent.parent / "personas" / "_builtin"
    if installed.exists():
        registry.register_dir(installed)
    # Development location: `packages/pantheon-core/personas/`.
    pkg_root = Path(__file__).resolve().parents[3]  # .../packages/pantheon-core
    dev = pkg_root / "personas"
    if dev.exists():
        registry.register_dir(dev)


_autoload_builtins()
