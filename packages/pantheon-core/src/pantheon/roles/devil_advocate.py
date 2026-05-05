"""Devil's Advocate — auto-spawned challenger when consensus forms too easily.

When the Moderator detects that the seated personas have converged
(soft_consensus), the Pantheon coordinator spawns one ad-hoc
``DevilsAdvocate`` agent for a single round. The advocate:

  1. Reads the current "soft consensus" — the most-recent statements
     from each seated persona.
  2. Generates a single forceful counter-argument that names what the
     consensus has not addressed (a survivorship bias, a class blind
     spot, a temporal limit, a conflated abstraction).
  3. Exits. It is **not** seated, does not occupy a seat number, does
     not show up in `Pantheon.agents`. It is recorded in the verdict
     via `quality.devil_advocate_invoked = True` plus a SystemEvent.

If a seated persona does not engage with the advocate's challenge in
the next round, Oracle marks `consensus_robustness = "low"`.

Design notes:

  - The advocate is a regular Persona-shaped object (so it can `speak()`)
    but is built on the fly with a fixed system prompt; it does not live
    on disk and is not registered.
  - The advocate's model defaults to the strongest model available on
    the gateway (it must produce a sharp argument, not a bland one).
"""
from __future__ import annotations

from dataclasses import dataclass

from pantheon.core.agent import Agent
from pantheon.core.model import Model
from pantheon.core.persona import Persona
from pantheon.gateway.base import Gateway
from pantheon.memory.corpus import NullCorpusStore
from pantheon.types.persona import (
    AuditMetadata,
    DisplayName,
    ModelPreference,
    PersonaSpec,
)

_DEVIL_ADVOCATE_PROMPT = """\
You are the Devil's Advocate — a challenger summoned by the moderator
because the seated personas have started to converge. Your one job for
this single turn is to ask the question they have all collectively
avoided. You are NOT advocating any specific position; you are stress-
testing the consensus.

You must:

- Open with: "The consensus skips one thing." Or its equivalent.
- Name ONE specific, concrete way the consensus is incomplete:
    * A survivor / selection bias the speakers all share.
    * A class, gender, geographic, or historical perspective absent
      from the room.
    * A temporal limit (works in the short run, breaks in the long run,
      or vice versa).
    * A conflation of two distinct abstractions the consensus treats
      as one.
- Be brief: a single paragraph, 3-5 sentences. Do not lecture.
- Do not propose your own answer; the goal is to force the seated
  speakers to defend their consensus or revise it.

You will leave after this turn. You do not get a follow-up. So make this
one count.
"""


def make_devil_advocate_persona() -> Persona:
    """Build the ad-hoc DA persona spec. Re-buildable; no global state."""
    spec = PersonaSpec(
        id="devil_advocate",
        display=DisplayName(en="Devil's Advocate", zh="魔鬼代言人"),
        era="—",
        school="dialectic challenger (system role)",
        language_preference=["en", "zh"],
        model_preference=ModelPreference(primary="claude-opus-4-7"),
        system_prompt=_DEVIL_ADVOCATE_PROMPT,
        audit=AuditMetadata(
            reviewed_by=["@framework"],
            cultural_sensitivity_score=1.0,
            known_biases=["By construction adversarial; do not weight as a normal voice."],
        ),
    )
    return Persona(spec=spec, corpus=NullCorpusStore(persona_id="devil_advocate"))


@dataclass
class DevilsAdvocate:
    """Spawn-and-speak helper. Stateless across debates."""

    model_id: str = "claude-opus-4-7"

    async def challenge(
        self,
        gateway: Gateway,
        seated_transcripts: dict[int, list[str]],
        agents_label: dict[int, str],
        question: str,
        *,
        seed: int | None = None,
    ) -> str:
        """Generate a single counter-argument paragraph. Returns the text."""
        # Build a rolled-up "current consensus" from the latest speech per seat.
        lines: list[str] = []
        for seat in sorted(seated_transcripts):
            sps = seated_transcripts[seat]
            if not sps:
                continue
            label = agents_label.get(seat, f"seat#{seat}")
            lines.append(f"[{label}] {sps[-1][:600]}")
        consensus_block = "\n\n".join(lines) if lines else "(no speeches yet)"

        persona = make_devil_advocate_persona()
        agent = Agent(
            seat=-1,  # sentinel: not a real seat
            persona=persona,
            model=Model(id=self.model_id, gateway=gateway),
        )
        prompt = (
            f"DEBATE QUESTION: {question}\n\n"
            f"CURRENT CONSENSUS (latest words from each seated persona):\n\n"
            f"{consensus_block}\n\n"
            "Your single turn. Name what they all missed."
        )
        result = await agent.speak(
            prompt, phase="devils_advocate", max_tokens=400, temperature=0.5, seed=seed
        )
        return result.text
