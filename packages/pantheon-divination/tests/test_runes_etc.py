"""Runes + astrology + ziwei + contextualize."""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def pd():
    import pantheon_divination
    p = importlib.reload(pantheon_divination)
    p.accept_disclaimer()
    return p


def test_runes_three_rune(pd):
    r = pd.runes.cast(question="?", spread="three_rune", seed=1)
    assert len(r.lines) == 3
    assert r.method == "runes"


def test_runes_deterministic(pd):
    a = pd.runes.cast(question="Q?", seed=42)
    b = pd.runes.cast(question="Q?", seed=42)
    assert a.raw_state == b.raw_state


def test_astrology_without_skyfield_raises(pd):
    """Skyfield is not installed in CI; cast should raise the right error."""
    try:
        import skyfield  # noqa: F401
        pytest.skip("skyfield is installed; skip the no-skyfield test")
    except ImportError:
        pass
    # Note: importlib.reload of pd creates a fresh DivinationUnavailable
    # class object, while submodules captured the pre-reload class. Check
    # by class name + message rather than by isinstance.
    with pytest.raises(Exception) as ei:
        pd.astrology.cast(question="?")
    assert type(ei.value).__name__ == "DivinationUnavailable"
    assert "astrology" in str(ei.value)


def test_ziwei_stub_returns_placeholder(pd):
    r = pd.ziwei.cast(question="?", seed=1)
    assert r.method == "ziwei"
    assert "stub" in r.structured["implementation_status"]


@pytest.mark.asyncio
async def test_contextualize_strict_mode_skips_llm(pd):
    r = pd.iching.cast(question="Q?", seed=1)
    out = await pd.contextualize(r, judge=None, strict=True)
    assert "Method: iching" in out
    assert "Headline:" in out
    assert "Not a prediction" in out


@pytest.mark.asyncio
async def test_contextualize_uses_judge(pd):
    from pantheon import Model, MockGateway, ScriptedReply
    gw = MockGateway()
    gw.add_reply(ScriptedReply(
        text="The Army hexagram, when seeded with this question, suggests preparation. "
             "Each line guides discipline. Consider whether you have rallied enough.",
        model_id="judge",
    ))
    judge = Model(id="judge", gateway=gw)
    r = pd.iching.cast(question="Q?", seed=1)
    out = await pd.contextualize(r, judge=judge)
    assert "Army" in out or "hexagram" in out
    assert "Not a prediction" in out  # disclaimer appended
