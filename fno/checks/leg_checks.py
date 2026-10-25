"""Per leg (story C3, criterion 2): every leg a decision needs must have its own valid quote by A4's rule (bid > 0,
ask > 0, bid <= ask, both sizes > 0, a trade in the contract today). No quote age is claimed: Groww gives none. A trade
needing an unusable leg is not opened, before any leg is priced (no legging cost)."""

from __future__ import annotations

from .data_checks import CheckSubject, DataCheck


class LegQuotesValid(DataCheck):
    name, prices_unverified = "leg quotes", False  # exits judge each leg themselves (E4: a pending exit per leg)

    def problems(self, subject: CheckSubject) -> list[str]:
        snapshot = subject.snapshot
        if snapshot is None:
            return []
        found = []
        for expiry, strike, kind in subject.legs:
            quote = snapshot.quote(expiry, strike, kind)
            problem = "no quote in the snapshot" if quote is None else quote.a4_problem
            if problem:
                found.append(f"{expiry} {strike:g} {kind}: {problem}")
        return found
