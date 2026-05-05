"""Template persona pack — replace this docstring + module name + entry
point name with your own.

The minimal pack contract is: provide_personas() returns a list of
``pantheon.core.persona.Persona`` instances. Pantheon discovers your
pack via the ``pantheon.personas`` entry point group declared in
pyproject.toml.

Optional: gate sensitive personas behind an ``accept_disclaimer()`` call.
The pattern below is verbatim from pantheon-pack-founders — copy and
adapt the disclaimer text + region check. If your pack doesn't need
gating, drop the ``_DISCLAIMER_ACCEPTED`` machinery and have
``provide_personas()`` return personas unconditionally.
"""
from __future__ import annotations

import os
from pathlib import Path

_DISCLAIMER_ACCEPTED = False

DISCLAIMER_TEXT = """\
Replace this with your pack's disclaimer — what is being simulated,
what users should NOT do with the output, and any region restrictions.
"""


class PackUnavailable(RuntimeError):
    """Raised when the pack refuses to load (region or policy reasons)."""


def accept_disclaimer() -> None:
    """Acknowledge the disclaimer and unlock loading."""
    global _DISCLAIMER_ACCEPTED
    region = os.environ.get("PANTHEON_REGION", "").strip().lower()
    if region in {"cn"}:                # add your blocked-regions here
        raise PackUnavailable(
            f"This pack refuses to load in region={region!r}. "
            "Override responsibility lies with the user."
        )
    _DISCLAIMER_ACCEPTED = True


_PERSONAS_ROOT = Path(__file__).parent.parent.parent / "personas"
if not _PERSONAS_ROOT.exists():
    # Wheel-installed location.
    _PERSONAS_ROOT = Path(__file__).parent / "personas"


def provide_personas() -> list:
    """Pantheon entry-point hook. Returns nothing until accept_disclaimer()."""
    if not _DISCLAIMER_ACCEPTED:
        return []
    from pantheon.core.persona import load_persona
    out = []
    for d in sorted(_PERSONAS_ROOT.iterdir()):
        yaml = d / "persona.yaml"
        if yaml.exists():
            out.append(load_persona(yaml))
    return out


def register() -> int:
    """Convenience: register all of this pack's personas into the global
    ``pantheon.registry``. Returns the count registered."""
    from pantheon.core.persona import registry
    if not _DISCLAIMER_ACCEPTED:
        raise PackUnavailable(
            "Call accept_disclaimer() before register()."
        )
    n = 0
    for p in provide_personas():
        registry.register(p)
        n += 1
    return n


__version__ = "0.0.1"
__all__ = [
    "DISCLAIMER_TEXT",
    "PackUnavailable",
    "accept_disclaimer",
    "provide_personas",
    "register",
]
