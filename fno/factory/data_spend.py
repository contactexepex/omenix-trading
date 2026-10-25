"""G2, the data spend (FACTORY_RULES section 4): the rows of `research/DATA_SPEND.md` an idea's test reads.

A row `spent` or `exposed` makes the test exploratory (it cannot pass G6); `fresh` and `forward` rows are fresh. A
`registered` row is fresh only for a trial its "Used by" cell names (its own reservation); for any other trial it
counts as exploratory, the strict reading. The register is a hand-kept table: R1 reads and checks it, never writes
it."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .constants import Outcome
from .fields import CardError

_REGISTER_HEADING = "## Register"
_FRESH, _USED = ("fresh", "forward"), ("spent", "exposed")
_REGISTERED = "registered"


@dataclass(frozen=True)
class SpendRow:
    key: str  # "data set | price type | period", as the card names it
    status: str
    used_by: str


@dataclass(frozen=True)
class SpendVerdict:
    outcome: Outcome
    rows: tuple[SpendRow, ...]
    not_fresh: tuple[SpendRow, ...]  # the rows that make the test exploratory


def parse_register(text: str) -> dict[str, SpendRow]:
    if _REGISTER_HEADING not in text:
        raise CardError(f"the data-spend register has no '{_REGISTER_HEADING}' table")
    lines = text.split(_REGISTER_HEADING, 1)[1].strip().splitlines()
    rows = {}
    for line in lines[2:]:  # past the header and its rule
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        row = SpendRow(" | ".join(cells[:3]), cells[3].strip("`"), cells[4])
        rows[row.key] = row
    return rows


def _fresh_for(row: SpendRow, trial_id: str) -> bool:
    if row.status == _REGISTERED:
        return re.search(rf"(?<![\d-]){re.escape(trial_id)}(?![\d-])", row.used_by) is not None
    if row.status not in (*_FRESH, *_USED):
        raise CardError(f"data-spend row '{row.key}' has an unknown status '{row.status}'")
    return row.status in _FRESH


def data_spend(register: dict[str, SpendRow], data_sets: list[str], trial_id: str, where: str) -> SpendVerdict:
    missing = [key for key in data_sets if key not in register]
    if missing:
        raise CardError(f"{where}: field 'data_sets' names '{missing[0]}', which is not a row of the register")
    rows = tuple(register[key] for key in data_sets)
    not_fresh = tuple(row for row in rows if not _fresh_for(row, trial_id))
    return SpendVerdict(Outcome.EXPLORATORY if not_fresh else Outcome.FRESH, rows, not_fresh)
