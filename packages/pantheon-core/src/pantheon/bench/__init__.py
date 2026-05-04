"""Model capability registry — `models.yaml` seed + user override.

Per plan §5.3, model capability is hand-curated v0 from public benchmarks
(LiveBench, EQ-Bench, CMMLU, MT-Bench, etc.). Users override locally at
``~/.pantheon/models.local.yaml`` (highest priority).

The 7 dimensions match the persona-skill dimensions, so weight composition
in `compute_weights` is a clean cosine without translation. A model's
capability vector says "how good is this LLM at producing high-quality
output ABOUT this dimension" — separate from the persona's domain
expertise.

`pantheon-bench` (community-maintained, M3 stretch) will produce PRs
into this file with measured numbers from a calibration suite.
"""
from pantheon.bench.registry import (
    ModelCapability,
    capability_for,
    load_models_yaml,
    models_registry,
)

__all__ = [
    "ModelCapability",
    "capability_for",
    "load_models_yaml",
    "models_registry",
]
