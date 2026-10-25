"""What one source's slot captured: its rows and the raw-answer lines for Drive; and the near-month and near-money
choices both readers share (story MS-P0b section 2: the first listed monthly expiry, the ATM strike nearest the
future's last price, ATM +-2 listed strikes)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from .answers import UNEXPECTED, RawAnswer
from .caller import SourceStopped
from .constants import STRIKES_EACH_SIDE
from .rows import CaptureRow

LotLookup = Callable[[str, date], "int | None"]
PARSE_ERRORS = (KeyError, TypeError, ValueError, AttributeError, IndexError)


@dataclass
class SlotCapture:
    rows: list[CaptureRow] = field(default_factory=list)
    lines: list[dict] = field(default_factory=list)

    def keep(self, request: str, first_seen: datetime, answer: RawAnswer) -> str:
        """Keeps the raw answer for Drive and returns its SHA-256."""
        digest = answer.sha256()
        self.lines.append({"request": request, "first_seen": first_seen.isoformat(), "sha256": digest,
                           "answer": answer.payload})  # fmt: skip
        return digest

    def all_lines(self) -> list[dict]:
        return self.lines + [row.as_line() for row in self.rows]


def near_monthly(expiries: list[date], session: date) -> date | None:
    """The near-month contract's expiry: the last listed expiry in the month of the first one on or after the session
    (a weekly list holds several in that month; the monthly is the last)."""
    ahead = sorted(e for e in expiries if e >= session)
    if not ahead:
        return None
    return max(e for e in ahead if (e.year, e.month) == (ahead[0].year, ahead[0].month))


def near_money(strikes: list[float], reference: float) -> list[float]:
    """ATM (the listed strike nearest `reference`) and the listed strikes either side of it."""
    ordered = sorted(set(strikes))
    if not ordered or reference <= 0:
        return []
    at = min(range(len(ordered)), key=lambda i: abs(ordered[i] - reference))
    return ordered[max(0, at - STRIKES_EACH_SIDE) : at + STRIKES_EACH_SIDE + 1]


def parsed(read: Callable[[], object]):
    """The value `read` builds from an answer; an answer it cannot read stops the source cleanly (self-review 4)."""
    try:
        return read()
    except PARSE_ERRORS:
        raise SourceStopped(UNEXPECTED) from None
