"""A book's paper trades of one strategy version, counted from its desk records (story E6), for D2's allocation rule
(`StrategyTradeCounts`: an unproven version, below 20 completed trades, holds at most one open trade). A completed
trade opened and has closed; an entry unwound at once never opened, so it is not one."""

from __future__ import annotations

from ..books.equity import trade_positions
from ..constants import OUTCOME_OPENED
from .records import DeskRecords


def version_tag(name: str, version: int) -> str:
    """The version as desk records name it: `<name>-v<n>`."""
    return f"{name}-v{version}"


def version_key(tag: str) -> tuple[str, int]:
    """`<name>-v<n>` -> (name, n): the playbook key of a desk record's version."""
    name, _, number = tag.rpartition("-v")
    return name, int(number)


class DeskTradeCounts:
    def __init__(self, records: DeskRecords):
        self.records = records

    def _opened(self, name: str, version: int) -> list[bool]:
        """For each opened trade of the version: is it still open?"""
        tag, trades = version_tag(name, version), trade_positions(self.records.account.fills())
        opened = {
            e["trade_id"] for e in self.records.event_rows() if e["strategy"] == tag and e["outcome"] == OUTCOME_OPENED
        }
        return [trades[t].is_open for t in sorted(opened) if t in trades]

    def completed(self, name: str, version: int) -> int:
        return sum(not still_open for still_open in self._opened(name, version))

    def open(self, name: str, version: int) -> int:
        return sum(self._opened(name, version))
