"""The driver brake's state (story 3.3 law 7; owner, 22 Oct 2026, "Pause till monthly review"), from the account's
equity rows (one per session, at that slot's marks before its fills) and the monthly review rows that lift it.

- The high is the highest fully marked equity since the account opened, or since the brake was last lifted.
- The brake engages on the first fully marked session whose equity is `brake_rs` or more below that high, and holds
  across sessions whatever equity does next.
- A review row dated on or after the engagement and before a session lifts it from that session; the high restarts
  at the next fully marked equity (until then, the latest row's). A review row with no brake engaged changes nothing.
- "Pause till monthly review" (owner, 22 Oct 2026; story section 6 item 5): the review is on or after the first
  Saturday of the month after the engagement. A row dated from the engagement to the day before that Saturday is an
  error (`ReviewFileError`), never a lift: an early or mistaken row cannot turn a month's pause into a day's.
- A session with an unmarked position (counted at its worst case) neither sets the high nor engages the brake: one
  missing quote never pauses a driver for a month. Its own decision is still checked against its own equity."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from .reviews import ReviewFileError

SATURDAY = 5  # date.weekday()


@dataclass(frozen=True)
class EquityRow:
    session: date
    equity: float
    fully_marked: bool


@dataclass(frozen=True)
class BrakeState:
    high: float
    engaged_on: date | None
    lifted_on: date | None


def first_review_day(engaged: date) -> date:
    """The first Saturday of the month after `engaged`."""
    first = date(engaged.year + engaged.month // 12, engaged.month % 12 + 1, 1)
    return first + timedelta(days=(SATURDAY - first.weekday()) % 7)


def brake_state(rows: Sequence[EquityRow], lifts: Sequence[date], brake_rs: float) -> BrakeState:
    high: float | None = None
    engaged: date | None = None
    lifted: date | None = None
    rows = sorted(rows, key=lambda r: r.session)
    for row in rows:
        lifting = [day for day in lifts if engaged is not None and engaged <= day < row.session]
        early = [day for day in lifting if day < first_review_day(engaged)]
        if early:
            raise ReviewFileError(f"review row {early[0]} is before the monthly review ({first_review_day(engaged)})")
        if lifting:
            engaged, lifted, high = None, max(lifting), None  # the high restarts at the next fully marked row
        if not row.fully_marked:
            continue
        high = row.equity if high is None else max(high, row.equity)
        if engaged is None and high - row.equity >= brake_rs:
            engaged = row.session
    if not rows:
        raise ValueError("the brake needs at least the account's opening row")
    return BrakeState(rows[-1].equity if high is None else high, engaged, lifted)
