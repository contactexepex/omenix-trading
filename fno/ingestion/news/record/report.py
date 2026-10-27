"""What one `news promote` run did, in counts and fixed codes only (invariant 1 of P2): never a feed, URL or title."""

from __future__ import annotations

from collections import Counter

from fno.ingestion.news import codes

RECORDED, REVISIONS, NO_OPS = "recorded", "revisions", "no_ops"
POLLS, ITEMS = "polls", "items"
OUTCOME_KEYS = (RECORDED, REVISIONS, NO_OPS)


class PromotionReport:
    def __init__(self) -> None:
        self.outcomes: Counter[str] = Counter()  # polls, items, recorded, revisions, no_ops
        self.rejected: Counter[str] = Counter()  # fixed code -> number of items or polls left unpromoted

    def reject(self, code: str, number: int = 1) -> None:
        self.rejected[code] += number

    def poll_done(self, items: int, outcomes: Counter[str], failed: int, rejected: int) -> None:
        """Adds one poll and checks items = recorded + revisions + no-ops + failed + rejected (nothing went missing)."""
        self.outcomes[POLLS] += 1
        self.outcomes[ITEMS] += items
        self.outcomes.update(outcomes)
        if items != sum(outcomes[k] for k in OUTCOME_KEYS) + failed + rejected:
            self.reject(codes.NOT_RECONCILED)

    @property
    def ok(self) -> bool:
        return not self.rejected

    def line(self) -> str:
        done = ", ".join(f"{k} {self.outcomes[k]}" for k in (POLLS, ITEMS, *OUTCOME_KEYS))
        stuck = "".join(f", {code} {n}" for code, n in sorted(self.rejected.items()))
        return f"news promote: {done}{stuck}"
