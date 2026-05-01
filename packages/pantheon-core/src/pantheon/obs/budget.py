"""BudgetGuard — hard limits on cost / call-count / wall-clock per session.

The guard is checked **before** each LLM call. On breach it raises
`BudgetExceeded` and records the breach. The session can be `resume()`-d with
a fresh budget — the guard never silently degrades.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    """Raised when a BudgetGuard limit is hit. Session can be resumed."""


@dataclass
class BudgetGuard:
    max_usd: float = 10.0
    max_calls: int = 200
    max_minutes: float = 15.0

    spent_usd: float = field(default=0.0, init=False)
    calls_made: int = field(default=0, init=False)
    started_at: float = field(default_factory=time.monotonic, init=False)

    def check(self) -> None:
        if self.calls_made >= self.max_calls:
            raise BudgetExceeded(
                f"max_calls={self.max_calls} reached (made {self.calls_made})"
            )
        if self.spent_usd >= self.max_usd:
            raise BudgetExceeded(f"max_usd={self.max_usd} reached (spent {self.spent_usd:.4f})")
        elapsed_min = (time.monotonic() - self.started_at) / 60
        if elapsed_min >= self.max_minutes:
            raise BudgetExceeded(f"max_minutes={self.max_minutes} reached")

    def record(self, cost_usd: float) -> None:
        self.spent_usd += cost_usd
        self.calls_made += 1

    def reset(self) -> None:
        self.spent_usd = 0.0
        self.calls_made = 0
        self.started_at = time.monotonic()

    def remaining(self) -> dict[str, float]:
        return {
            "usd": max(0.0, self.max_usd - self.spent_usd),
            "calls": max(0, self.max_calls - self.calls_made),
            "minutes": max(0.0, self.max_minutes - (time.monotonic() - self.started_at) / 60),
        }
