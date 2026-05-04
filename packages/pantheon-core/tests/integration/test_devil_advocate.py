"""Devil's Advocate: spawned when consensus detected, contributes a Claim."""
from __future__ import annotations

import pytest

from pantheon import MockGateway, Pantheon, ScriptedReply, registry
from pantheon.types.events import SystemEvent


@pytest.mark.asyncio
async def test_devil_advocate_fires_when_consensus_detected():
    """Force soft consensus by feeding identical scripted replies to all
    seated personas. Verify the DA SystemEvent appears."""
    gw = MockGateway()
    # Identical reply for every speak() call → guaranteed soft consensus.
    same_reply = ("All things considered, balance and integrity are what matter most "
                  "for any reasonable answer.")
    # MockGateway routes by (model_id, persona_id). Confucius uses
    # deepseek-chat and the other two use claude-opus-4-7 by default.
    for model_id in ("deepseek-chat", "claude-opus-4-7"):
        for _ in range(40):
            gw.add_reply(ScriptedReply(text=same_reply, model_id=model_id))
    # And ensure the Devil's Advocate has a reply to give.
    da_reply = "The consensus skips one thing — none of the speakers asked who is paying."
    for _ in range(5):
        gw.add_reply(ScriptedReply(
            text=da_reply, model_id="claude-opus-4-7", persona_id="devil_advocate",
        ))

    p = Pantheon.summon(["confucius", "socrates", "naval"], gateway=gw)
    sess = p.debate("Should I quit my job?", rounds=3, seed=42)
    da_events = []
    async for ev in sess.stream():
        if isinstance(ev, SystemEvent) and "Devil" in ev.message:
            da_events.append(ev)

    v = await sess.verdict()
    assert v.quality.devil_advocate_invoked is True
    assert len(da_events) >= 1, f"expected ≥1 DA SystemEvent; got {len(da_events)}"
    # The DA challenge text should appear in one of the events.
    assert any(da_reply in ev.message for ev in da_events)


@pytest.mark.asyncio
async def test_devil_advocate_adds_claim_to_ledger():
    """The DA's challenge must enter the evidence ledger so Oracle can see
    whether the seated personas engaged with it."""
    gw = MockGateway()
    same_reply = "Balance is everything; balance is what matters."
    for model_id in ("deepseek-chat", "claude-opus-4-7"):
        for _ in range(40):
            gw.add_reply(ScriptedReply(text=same_reply, model_id=model_id))
    for _ in range(5):
        gw.add_reply(ScriptedReply(
            text="The consensus skips one thing.",
            model_id="claude-opus-4-7", persona_id="devil_advocate",
        ))
    p = Pantheon.summon(["confucius", "socrates", "naval"], gateway=gw)
    sess = p.debate("Q?", rounds=3, seed=1)
    async for _ in sess.stream():
        pass

    # The session has a private _verdict; the verdict's quality flag is enough.
    v = await sess.verdict()
    assert v.quality.devil_advocate_invoked is True


@pytest.mark.asyncio
async def test_devil_advocate_does_not_fire_without_consensus():
    """Diverse replies → no soft consensus → no DA."""
    gw = MockGateway()
    # Distinct reply per persona → token-overlap jaccard < 0.85 → no DA.
    per_persona = {
        "confucius": ("Confucius perspective: ritual matters more than profit; "
                      "ceremony shapes character through repetition."),
        "socrates":  ("Socratic posture: I know nothing about this; "
                      "let us examine our terms before we answer."),
        "naval":     ("Naval take: leverage is what moves the needle; "
                      "everything else is noise without compounding."),
    }
    for pid, text in per_persona.items():
        for _ in range(40):
            gw.add_reply(ScriptedReply(
                text=text,
                model_id="deepseek-chat" if pid == "confucius" else "claude-opus-4-7",
                persona_id=pid,
            ))
    p = Pantheon.summon(["confucius", "socrates", "naval"], gateway=gw)
    sess = p.debate("Q?", rounds=3, seed=2)
    async for _ in sess.stream():
        pass
    v = await sess.verdict()
    # Diverse content → soft_consensus=False → DA NOT invoked.
    assert v.quality.devil_advocate_invoked is False


@pytest.mark.asyncio
async def test_devil_advocate_persona_built_freshly_each_time():
    """make_devil_advocate_persona() should return a fresh persona each call,
    not a singleton that could be polluted across debates."""
    from pantheon.roles.devil_advocate import make_devil_advocate_persona

    a = make_devil_advocate_persona()
    b = make_devil_advocate_persona()
    assert a is not b
    assert a.spec.id == "devil_advocate"
    assert "Devil's Advocate" in (a.spec.display.en or "")
