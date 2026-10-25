"""The common opportunity set of a day (story E2, scoreboard A): every (approved version, expiry) eligible under its
playbook version, by D2's own opportunity code (DRY), plus the "no trade" opportunity. "Approved" is the playbook's
status at the start of the day (`Playbook.status_on`, the rule D2 uses), so a rebuild gives the same set. A version
paused during the day stays in this set (it was a real opportunity); Book 1's own gate (`Playbook.approved_on`) drops
it at once, and its outcome is "no trade" (judges 72 and 74)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from ..playbook.loader import Playbook
from ..playbook.opportunities import BOOK, OpportunityFinder
from ..playbook.transitions import PAPER

NO_TRADE_OPPORTUNITY = {"opportunity_id": "no_trade"}


class OpportunitySet:
    def __init__(self, finder: OpportunityFinder):
        self.finder = finder

    def build(self, playbook: Playbook, day: date, monthly: Iterable[date]) -> list[dict]:
        monthly, status = tuple(monthly), playbook.status_on(day)  # the playbook's own start-of-day rule (D2)
        approved = [s for s in playbook.strategies if status.get(s.key) == PAPER]
        found = [o for s in approved for o in self.finder.find(s, day, monthly, BOOK)]
        entries = [
            {
                "opportunity_id": o.opportunity_id,
                "strategy": o.strategy.name,
                "version": o.strategy.version,
                "rule_sha256": o.strategy.parameters_sha256,
                "expiry": o.context.expiry.isoformat(),
                "entry_day": o.context.entry_day.isoformat(),
                "exit_day": o.context.exit_day.isoformat(),
            }  # fmt: skip
            for o in found
        ]
        return sorted(entries, key=lambda e: e["opportunity_id"]) + [NO_TRADE_OPPORTUNITY]
