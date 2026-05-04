"""Model capability registry loader.

Resolution order:
  1. ~/.pantheon/models.local.yaml      (highest priority)
  2. $PANTHEON_MODELS_FILE              (env override)
  3. Bundled seed at bench/models.yaml  (lowest)

Each later layer's entries override the earlier layer's, key-by-key.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pantheon.calibration.probes import DIMENSIONS


@dataclass
class ModelCapability:
    model_id: str
    skills: dict[str, float] = field(default_factory=dict)
    cultural_depth: dict[str, float] = field(default_factory=dict)

    @property
    def overall(self) -> float:
        """Crude overall capability — geometric mean across the 7 dims.
        Used by `compute_weights` when no topic vector is available."""
        if not self.skills:
            return 0.5
        vals = [max(0.05, self.skills.get(d, 0.5)) for d in DIMENSIONS]
        prod = 1.0
        for v in vals:
            prod *= v
        return prod ** (1 / len(vals))

    def for_dimension(self, dim: str) -> float:
        return float(self.skills.get(dim, 0.5))


def _bundled_yaml_path() -> Path:
    return Path(__file__).with_name("models.yaml")


def _local_yaml_path() -> Path:
    if "PANTHEON_MODELS_FILE" in os.environ:
        return Path(os.environ["PANTHEON_MODELS_FILE"])
    return Path.home() / ".pantheon" / "models.local.yaml"


def _parse_yaml(path: Path) -> dict[str, ModelCapability]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    models = raw.get("models") or {}
    out: dict[str, ModelCapability] = {}
    for mid, fields in models.items():
        skills: dict[str, float] = {}
        cultural: dict[str, float] = {}
        for k, v in (fields or {}).items():
            if k.startswith("cultural_depth_"):
                cultural[k[len("cultural_depth_") :]] = float(v)
            elif k in DIMENSIONS:
                skills[k] = float(v)
        out[mid] = ModelCapability(
            model_id=mid, skills=skills, cultural_depth=cultural
        )
    return out


def load_models_yaml() -> dict[str, ModelCapability]:
    """Return the resolved models registry (bundled + local override)."""
    out = _parse_yaml(_bundled_yaml_path())
    out.update(_parse_yaml(_local_yaml_path()))
    return out


# Cached at module import; callers that mutate user override at runtime
# should call `models_registry.cache_clear()` and re-read.
class _Cache:
    def __init__(self) -> None:
        self._data: dict[str, ModelCapability] | None = None

    def __call__(self) -> dict[str, ModelCapability]:
        if self._data is None:
            self._data = load_models_yaml()
        return self._data

    def cache_clear(self) -> None:
        self._data = None


models_registry = _Cache()


def capability_for(model_id: str) -> ModelCapability:
    """Look up a model's capability. Unknown ids get a 0.5 default vector
    so weight composition stays defined."""
    reg = models_registry()
    if model_id in reg:
        return reg[model_id]
    return ModelCapability(
        model_id=model_id,
        skills={d: 0.5 for d in DIMENSIONS},
        cultural_depth={"en": 0.5, "zh": 0.5},
    )
