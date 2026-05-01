"""Replay — same debate, deterministic re-run from JSONL recording."""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from pantheon import MockGateway, Pantheon


async def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["PANTHEON_SESSIONS_DIR"] = tmp

        p = Pantheon(gateway=MockGateway())
        for pid in ["confucius", "socrates", "naval"]:
            from pantheon import Agent, Model, registry

            persona = registry.get(pid)
            seat = len(p.agents) + 1
            p.add_agent(
                Agent(seat=seat, persona=persona, model=Model(id=persona.spec.model_preference.primary, gateway=p.gateway))
            )

        sess1 = p.debate("Is patience always a virtue?", rounds=3, seed=7)
        v1 = await sess1.run()

        # Now replay
        recording = Path(tmp) / f"{v1.debate_id}.jsonl"
        assert recording.exists(), f"missing recording at {recording}"

        # Build a new Pantheon and replay through ReplayGateway.
        p2 = Pantheon(gateway=MockGateway())
        for pid in ["confucius", "socrates", "naval"]:
            from pantheon import Agent, Model, registry

            persona = registry.get(pid)
            seat = len(p2.agents) + 1
            p2.add_agent(
                Agent(seat=seat, persona=persona, model=Model(id=persona.spec.model_preference.primary, gateway=p2.gateway))
            )

        sess2 = p2.debate(
            "Is patience always a virtue?",
            rounds=3,
            seed=7,
            replay_from=recording,
            record=False,
        )
        v2 = await sess2.run()
        print(f"original  debate_id={v1.debate_id}  calls={v1.model_calls}")
        print(f"replayed  debate_id={v2.debate_id}  calls={v2.model_calls}")
        assert v1.debate_id == v2.debate_id, "debate_id should be deterministic across replay"
        print("✓ replay produced an identically-ID'd debate")


if __name__ == "__main__":
    asyncio.run(main())
