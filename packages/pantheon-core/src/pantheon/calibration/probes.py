"""Probes loader — 7 skill dimensions × N prototype questions."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

# Canonical 7 dimensions. Order matters for deterministic output.
DIMENSIONS: tuple[str, ...] = (
    "ethics",
    "governance",
    "education",
    "business",
    "technology",
    "divination",
    "emotion",
)


@dataclass
class Probes:
    schema_version: str
    questions: dict[str, list[str]]  # dimension → questions

    def for_dimension(self, dim: str) -> list[str]:
        return self.questions.get(dim, [])

    def all_dimensions(self) -> tuple[str, ...]:
        return DIMENSIONS


def _default_probes_path() -> Path:
    return Path(__file__).with_name("probes.yaml")


def load_probes(path: str | Path | None = None) -> Probes:
    p = Path(path) if path else _default_probes_path()
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    schema = raw.pop("schema_version", "1.0")
    raw.pop("description", None)
    questions = {dim: list(raw.get(dim, [])) for dim in DIMENSIONS}
    missing = [d for d, qs in questions.items() if not qs]
    if missing:
        raise ValueError(f"probes.yaml is missing questions for dimensions: {missing}")
    return Probes(schema_version=str(schema), questions=questions)
