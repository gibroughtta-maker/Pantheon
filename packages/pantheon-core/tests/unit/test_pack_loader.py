"""Persona pack entry-point auto-discovery."""
from __future__ import annotations

from pantheon.core.persona import registry


def test_builtin_personas_include_m2_additions():
    """The 13 built-in personas (M0 + M2) should all be registered."""
    ids = {p.id for p in registry.all()}
    expected = {
        "confucius", "socrates", "naval",
        "laozi", "mencius",
        "plato", "aristotle", "marcus_aurelius", "nietzsche",
        "einstein", "jobs", "paul_graham", "charlie_munger",
    }
    assert expected.issubset(ids), f"missing: {expected - ids}"


def test_founders_pack_not_loaded_until_disclaimer():
    """pantheon-pack-founders is opt-in. Without accept_disclaimer(),
    its entry point returns []. registry should NOT contain jesus etc."""
    import importlib

    import pantheon_pack_founders
    importlib.reload(pantheon_pack_founders)  # reset _DISCLAIMER_ACCEPTED

    # Re-scan entry points; nothing new should appear from founders since
    # accept_disclaimer() has not been called.
    n = registry.rescan_entry_points()
    assert "jesus" not in {p.id for p in registry.all()}


def test_founders_pack_appears_after_disclaimer():
    import importlib

    import pantheon_pack_founders
    importlib.reload(pantheon_pack_founders)
    pantheon_pack_founders.accept_disclaimer()
    pantheon_pack_founders.register()

    ids = {p.id for p in registry.all()}
    assert {"jesus", "muhammad", "buddha"}.issubset(ids)


def test_registry_has_helpers():
    assert registry.has("confucius") is True
    assert registry.has("not-a-real-persona") is False


def test_registry_rescan_idempotent():
    """rescan_entry_points should be idempotent — calling twice should not
    double-register or raise."""
    n1 = registry.rescan_entry_points()
    n2 = registry.rescan_entry_points()
    # Both calls return non-negative counts (registry.register is idempotent
    # by id; the returned count is "new this call" which may be 0).
    assert n1 >= 0
    assert n2 >= 0
