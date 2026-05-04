"""紫微斗数 — chart computation. Stub for M4 (full implementation is M4+).

紫微斗数 chart construction requires:
  - lunar/solar calendar conversion for the birth date
  - 12 palaces (命宫, 兄弟宫, 夫妻宫, ...)
  - 14 main stars (紫微, 天机, 太阳, 武曲, ...)
  - 6 auxiliary stars and 4 transformations

A minimally faithful implementation needs ~1500 lines of canonical
positioning logic, which is out of scope for the M4 ship. This stub
returns a placeholder DivinationResult; users are pointed at
established libraries (e.g. py-iztro) and a roadmap link.
"""
from __future__ import annotations

from pantheon_divination import _ensure_accepted
from pantheon_divination.types import DivinationLine, DivinationResult


def cast(
    question: str,
    *,
    birth_year: int | None = None,
    birth_month: int | None = None,
    birth_day: int | None = None,
    birth_hour: int | None = None,
    seed: int = 0,
) -> DivinationResult:
    _ensure_accepted()
    return DivinationResult(
        method="ziwei",
        question=question,
        seed=seed,
        headline_zh="紫微斗数",
        headline_en="Ziwei Doushu",
        primary="(M4+ — full chart algorithm not yet implemented)",
        secondary="",
        judgment=(
            "紫微斗数排盘需要历法转换 + 14 主星 + 12 宫位的完整算法；"
            "本插件 M4 尚未交付。建议参考 py-iztro 等独立实现，"
            "或贡献此模块的 PR。"
        ),
        image="—",
        lines=[
            DivinationLine(
                position="status",
                text="ziwei.cast is a stub; see project roadmap for M4+ delivery.",
            )
        ],
        structured={
            "birth_year": str(birth_year or ""),
            "birth_month": str(birth_month or ""),
            "birth_day": str(birth_day or ""),
            "birth_hour": str(birth_hour or ""),
            "implementation_status": "stub",
        },
    )


__all__ = ["cast"]
