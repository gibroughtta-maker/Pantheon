"""Quickstart — three personas, MockGateway, no LLM bills.

Run: ``python examples/01_quickstart.py``
"""
from __future__ import annotations

import asyncio

from pantheon import MockGateway, Pantheon


async def main() -> None:
    p = Pantheon.summon(
        ["confucius", "socrates", "naval"],
        gateway=MockGateway(),
    )
    sess = p.debate(
        "Should I quit my job to do an indie startup?",
        rounds=3,
        seed=42,
    )
    verdict = await sess.run()
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    print("Question:", verdict.question)
    print()
    print("Consensus:")
    for c in verdict.consensus:
        print(f"  ({', '.join(c.supporters)}, w={c.weight:.2f}) {c.statement[:200]}")
    print("\nMinority:")
    for m in verdict.minority_opinion:
        print(f"  [{m.holder}] {m.statement[:200]}")
    print(f"\nrobustness={verdict.consensus_robustness}  "
          f"no_consensus={verdict.no_consensus}  "
          f"calls={verdict.model_calls}  "
          f"cost=${verdict.cost.total_usd:.4f}")
    print(f"debate_id={verdict.debate_id}")


if __name__ == "__main__":
    asyncio.run(main())
