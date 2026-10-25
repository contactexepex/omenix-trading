"""Story A14 criterion 1, per structure (judge 77, option a; story STR1b, review 100 point 4.4): the job writes a
structure's rows, which C2 trusts, only from the day an independent broker check of that structure's figures passed.
`config.yaml` `risk.margins.nse_span_check` maps each approved code to its check's `source` and `passed_on`. A code
without an approval, or a day before its `passed_on`, is printed and never written. A day before the first approval can
never get a row, so the job does not count it as pending (it would alert on every run for a week); with no approval at
all, the run writes nothing and is refused by name. Broker checks arrive one code at a time, so adding a code never
moves another's date."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from ..constants import STRUCTURES, STRUCTURES_ONE_SIDE

CHECK_KEY = "nse_span_check"
NOT_PASSED = (
    "{rows} rows computed, none written: no independent broker check has passed for any structure by this day "
    f"(config.yaml risk.margins.{CHECK_KEY}: code -> source and passed_on; story A14 criterion 1, judge 77)"
)
SHAPE = f"{CHECK_KEY} must map structure codes to {{source, passed_on}}, e.g. SF: {{source: ..., passed_on: ...}}"


@dataclass(frozen=True)
class Approval:
    source: str  # where the passing check is recorded, e.g. the owner's Groww check in a claims file
    passed_on: date


@dataclass(frozen=True)
class BrokerApprovals:
    by_code: Mapping[str, Approval]

    def approves(self, structure: str, day: date) -> bool:
        approval = self.by_code.get(structure)
        return approval is not None and approval.passed_on <= day

    def any_by(self, day: date) -> bool:
        return any(approval.passed_on <= day for approval in self.by_code.values())

    def first_day(self) -> date | None:
        """The first day any structure may be written; None when nothing is approved."""
        return min((approval.passed_on for approval in self.by_code.values()), default=None)

    @classmethod
    def from_margins_block(cls, margins: Mapping[str, Any]) -> BrokerApprovals:
        """The approvals from `risk.margins`; no block means none. Anything else than the map is refused."""
        block = margins.get(CHECK_KEY) or {}
        if not isinstance(block, Mapping):
            raise ValueError(SHAPE)
        return cls({code: _approval(code, entry) for code, entry in block.items()})


def _approval(code: str, entry: Any) -> Approval:
    if code not in (*STRUCTURES, *STRUCTURES_ONE_SIDE) or not isinstance(entry, Mapping):
        raise ValueError(f"{SHAPE}; not {code!r}: {entry!r}")
    source, passed_on = entry.get("source"), entry.get("passed_on")
    if isinstance(passed_on, str):
        passed_on = date.fromisoformat(passed_on)
    if not source or not isinstance(passed_on, date):
        raise ValueError(f"{CHECK_KEY}.{code} needs a source and a passed_on date, not {entry!r}")
    return Approval(source, passed_on)
