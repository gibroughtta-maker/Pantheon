"""Write calibration results back to a persona.yaml.

Updates `skills:` and `audit.calibration` blocks in place. Manual-review
dimensions are NOT auto-written; the CLI emits a `manual_review/<id>.md`
stub for the human to fill in.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from pantheon.calibration.runner import CalibrationResult


def write_calibration_metadata(
    persona_yaml_path: str | Path,
    result: CalibrationResult,
    *,
    apply_flagged: bool = False,
) -> dict:
    """Update persona.yaml in place with calibration result.

    Returns the updated dict for inspection.
    """
    p = Path(persona_yaml_path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))

    # Skills block: only write non-flagged dims unless apply_flagged.
    skills = dict(raw.get("skills") or {})
    for dim, score in result.final.items():
        if (dim not in result.flags) or apply_flagged:
            skills[dim] = score
    raw["skills"] = skills

    audit = dict(raw.get("audit") or {})
    audit["calibration"] = {
        "method": result.method,
        "run_id": result.run_id,
        "run_at": result.run_at,
        "judges": list(result.judges),
        "anchors_used": list(result.anchors_used),
        "sigma_per_dim": result.sigma,
        "manual_overrides": audit.get("calibration", {}).get("manual_overrides", {}) or {},
    }
    raw["audit"] = audit

    p.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return raw


def write_manual_review_stub(
    out_path: str | Path,
    result: CalibrationResult,
) -> None:
    """Write a markdown stub for a human to resolve flagged dimensions."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Manual review: {result.persona_id} (run {result.run_id})",
        "",
        f"L2 + L4 disagreed by > threshold on {len(result.flags)} dimension(s).",
        "Resolve each below; the value you choose will be applied to skills[<dim>]",
        "and recorded in audit.calibration.manual_overrides.",
        "",
    ]
    for dim in result.flags:
        l2_score = result.l2.by_dimension[dim].score
        l4_score = result.l4.by_dimension[dim].score if result.l4 else None
        lines.append(f"## {dim}")
        lines.append("")
        lines.append(f"- L2 (corpus coverage): **{l2_score}**")
        lines.append(f"- L4 (pairwise vs anchors): **{l4_score}**")
        lines.append(f"- |L2 − L4| = **{result.sigma[dim]}**")
        if result.l4 and dim in result.l4.by_dimension:
            wr = result.l4.by_dimension[dim].win_rate_vs_anchors
            lines.append(f"- L4 win rates vs anchors: {wr}")
        lines.append("")
        lines.append("**Decision:** _(write final score and 1-sentence rationale here)_")
        lines.append("")
        lines.append("```yaml")
        lines.append(f"{dim}:")
        lines.append("  value: 0.??")
        lines.append("  reason: 'TODO'")
        lines.append("```")
        lines.append("")
    p.write_text("\n".join(lines), encoding="utf-8")
