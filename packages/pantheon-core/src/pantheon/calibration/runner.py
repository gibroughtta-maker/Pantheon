"""Calibration runner — fuse L2 + L4, flag manual review, write metadata back.

Default fusion:  final[d] = w_l2 * L2[d] + w_l4 * L4[d]   (defaults 0.4, 0.6)
Disagreement σ:  abs(L2[d] - L4[d]) — when > threshold, the dimension is
flagged for manual review and the final score is left as the AVERAGE of the
two (not silently picking one), with the dim added to ``flags``.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pantheon.calibration.l2_retrieval import L2Result, score_l2
from pantheon.calibration.l4_pairwise import L4Result, score_l4
from pantheon.calibration.probes import DIMENSIONS, Probes, load_probes
from pantheon.core.model import Model
from pantheon.obs.replay import Recorder, default_session_dir


@dataclass
class CalibrationResult:
    persona_id: str
    run_id: str
    run_at: str
    method: str
    judges: list[str]
    anchors_used: list[str]
    probes_schema: str
    l2: L2Result
    l4: L4Result | None
    final: dict[str, float]
    sigma: dict[str, float]
    flags: list[str]  # dims flagged for manual review
    cost_usd: float = 0.0
    n_llm_calls: int = 0
    recording_path: str | None = None


async def run_calibration(
    target_persona,
    *,
    anchor_personas: list | None = None,
    judges: list[Model] | None = None,
    probes: Probes | None = None,
    fusion_weights: tuple[float, float] = (0.4, 0.6),  # (L2, L4)
    sigma_threshold: float = 0.2,
    seed: int | None = None,
    record_dir: str | Path | None = None,
) -> CalibrationResult:
    """Run a full calibration. Both L2 and L4 are run unless ``judges`` or
    ``anchor_personas`` is empty/None — in that case only L2 runs (L2-only mode).
    """
    probes = probes or load_probes()
    run_id = secrets.token_hex(8)
    run_at = datetime.now(UTC).isoformat()

    rec_dir = Path(record_dir) if record_dir else (default_session_dir().parent / "calibration")
    rec_dir.mkdir(parents=True, exist_ok=True)
    rec = Recorder(rec_dir / f"{run_id}.jsonl", debate_id=run_id)
    rec.write(
        "calibration_open",
        run_id=run_id,
        run_at=run_at,
        target=target_persona.id,
        anchors=[a.id for a in anchor_personas or []],
        judges=[j.id for j in judges or []],
        seed=seed,
        probes_schema=probes.schema_version,
    )

    l2 = await score_l2(target_persona.id, target_persona.corpus, probes)
    rec.write("calibration_l2", target=target_persona.id, l2=l2.vector(),
              by_dim={d: r.per_probe for d, r in l2.by_dimension.items()})

    l4: L4Result | None = None
    cost = 0.0
    n_calls = 0
    if anchor_personas and judges:
        # Track gateway cost via judges directly is tricky; just count calls.
        n_calls_before = sum(getattr(j.gateway, "_call_count", 0) for j in judges)
        l4 = await score_l4(target_persona, anchor_personas, probes, judges, seed=seed)
        n_calls = sum(len(probes.for_dimension(d)) for d in DIMENSIONS) * len(anchor_personas) * len(judges)
        rec.write("calibration_l4", target=target_persona.id, l4=l4.vector(),
                  raw_records=[r.__dict__ for r in l4.raw_records])
        _ = n_calls_before  # placeholder — full cost telemetry is M2

    method = "l2_l4_hybrid" if l4 else "l2_only"
    w_l2, w_l4 = fusion_weights
    final: dict[str, float] = {}
    sigma: dict[str, float] = {}
    flags: list[str] = []
    for dim in DIMENSIONS:
        s2 = l2.by_dimension[dim].score if dim in l2.by_dimension else 0.0
        s4 = l4.by_dimension[dim].score if (l4 and dim in l4.by_dimension) else None
        if s4 is None:
            final[dim] = round(s2, 4)
            sigma[dim] = 0.0
        else:
            sig = abs(s2 - s4)
            sigma[dim] = round(sig, 4)
            if sig > sigma_threshold:
                flags.append(dim)
                final[dim] = round((s2 + s4) / 2, 4)
            else:
                final[dim] = round(w_l2 * s2 + w_l4 * s4, 4)

    rec.write(
        "calibration_close",
        run_id=run_id,
        target=target_persona.id,
        final=final,
        sigma=sigma,
        flags=flags,
        method=method,
    )
    rec.close()

    return CalibrationResult(
        persona_id=target_persona.id,
        run_id=run_id,
        run_at=run_at,
        method=method,
        judges=[j.id for j in judges or []],
        anchors_used=[a.id for a in anchor_personas or []],
        probes_schema=probes.schema_version,
        l2=l2,
        l4=l4,
        final=final,
        sigma=sigma,
        flags=flags,
        cost_usd=cost,
        n_llm_calls=n_calls,
        recording_path=str(rec.path),
    )
