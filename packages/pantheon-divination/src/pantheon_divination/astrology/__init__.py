"""Astrology — real ephemerides via Skyfield (optional extra).

Install with:
    pip install pantheon-divination[astrology]

This module is a real-ephemerides implementation, not a sun-sign lookup.
Without Skyfield installed, ``cast()`` raises ``DivinationUnavailable``
with installation instructions.

M4 ships a minimal "current sky" cast that returns the longitude of the
Sun, Moon, and seven traditional planets in tropical zodiac signs at the
given UTC moment. Houses, aspects, and natal charts (which require birth
time + place) are M4+ stretches.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime, timezone

from pantheon_divination import DivinationUnavailable, _ensure_accepted
from pantheon_divination.types import DivinationLine, DivinationResult

_BODIES = (
    ("sun",      "Sun"),
    ("moon",     "Moon"),
    ("mercury",  "Mercury"),
    ("venus",    "Venus"),
    ("mars",     "Mars"),
    ("jupiter",  "Jupiter"),
    ("saturn",   "Saturn"),
)

_SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)


def _ecliptic_longitude_to_sign(lon_deg: float) -> tuple[str, float]:
    lon = lon_deg % 360.0
    sign = _SIGNS[int(lon // 30)]
    return sign, lon % 30.0


def cast(
    question: str,
    *,
    moment: datetime | None = None,
    seed: int = 0,
) -> DivinationResult:
    _ensure_accepted()
    try:
        from skyfield.api import load  # type: ignore[import-not-found]
    except ImportError as e:
        raise DivinationUnavailable(
            "astrology requires the 'astrology' extra. "
            "Install: pip install pantheon-divination[astrology]"
        ) from e

    moment = moment or datetime.now(tz=UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)

    ts = load.timescale()
    t = ts.from_datetime(moment)
    eph = load("de421.bsp")  # Skyfield-supplied 1900–2050 ephemeris
    earth = eph["earth"]

    div_lines: list[DivinationLine] = []
    primary_sign = ""
    for body_id, label in _BODIES:
        try:
            body = eph[body_id]
        except KeyError:
            continue
        ecl = earth.at(t).observe(body).apparent().ecliptic_position()
        # Convert XYZ to ecliptic longitude (degrees).
        x, y, _z = ecl.au
        lon = math.degrees(math.atan2(y, x)) % 360.0
        sign, deg = _ecliptic_longitude_to_sign(lon)
        if label == "Sun":
            primary_sign = sign
        div_lines.append(
            DivinationLine(
                position=label,
                text=f"{lon:.2f}° — {sign} {deg:.2f}°",
                extra={"longitude_deg": f"{lon:.4f}", "sign": sign, "deg_in_sign": f"{deg:.4f}"},
            )
        )

    return DivinationResult(
        method="astrology",
        question=question,
        seed=seed,
        headline_zh=f"日在{primary_sign}",
        headline_en=f"Sun in {primary_sign}",
        primary=f"Sun in {primary_sign}",
        secondary="",
        judgment="Sky positions at the given UTC moment.",
        image=f"Sun ☉ in {primary_sign}",
        lines=div_lines,
        structured={"moment_utc": moment.isoformat()},
        raw_state={"bodies_observed": [b for b, _ in _BODIES]},
    )


__all__ = ["cast"]
