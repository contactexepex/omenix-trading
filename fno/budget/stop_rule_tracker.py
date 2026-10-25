"""The whole-project stop rule's tracker (story BG1; design v2 section 8.2, owner decision of 15 Oct 2026). Review date:
the last session of the sixth full calendar month after protocol v4's freeze (the freeze's own month is not counted;
"session" is any NSE session, a special weekend session included: design 8.2 does not say, and it is immaterial for the
months seen). While v4 is not frozen the date is projected from the design's assumed freeze month and says so. Test A
and Test B are only reported as computable once every input they need exists; until then each reads "not computable
yet"."""

from __future__ import annotations

import calendar
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from ..constants import JOURNAL_FOLDER, SHADOW_FOLDER
from ..factory.constants import GATES_FILE
from ..research_data.calendar import CalendarError, SessionCalendar

FULL_MONTHS = 6
PROJECTED = "projected: depends on protocol v4 (story G6) freezing in {month}; each month later moves it a month"
DECIDED = "from protocol v4's freeze on {day}"
WEEKDAY_FALLBACK = (
    "the NSE calendar has no {year} rows, so the last weekday is used until NSE's {year} circular is added"
)
NOT_COMPUTABLE = "not computable yet"
REVIEW_REACHED = (
    "Omenix F&O SYSTEM: the stop-rule review date ({day:%d %b %Y}, {basis}) is reached: run Test A and Test B "
    "(design v2 section 8.2)"
)
UNCONFIRMED = "; the date is not confirmed: {notes}"
SHADOW_ACCOUNTS = f"{JOURNAL_FOLDER}/{SHADOW_FOLDER}"  # story R3: one folder per research version's shadow account
ZERO_SHADOWS = "at the review, zero eligible or resolved shadows gives undecided / no_economic_test, never no"


@dataclass(frozen=True)
class StopRuleInput:
    test: str
    what: str
    story: str
    path: str | None = None  # where the producing story writes it; None until that story defines it
    present: Callable[[Path], bool] | None = None  # when a file existing is not enough (story R1c, BG1 owner's design)

    def exists(self, root: Path) -> bool:
        if self.present is not None:
            return self.present(root)
        return self.path is not None and (root / self.path).exists()


def _shadows_registered(root: Path) -> bool:
    """Test B's R1 input is present only once a shadow is registered (G4), not when the gate log merely exists."""
    from ..factory.wiring import build_registered_shadows  # lazy: the budget does not load the factory otherwise

    return bool(build_registered_shadows(root).all())


INPUTS = (
    StopRuleInput("A", "protocol v4's registered family, frozen (primary comparisons, judgeable questions)", "G6"),
    StopRuleInput("A", "v4 daily scores of V6, V1 and V2 against their primary baselines", "G8"),
    StopRuleInput("A", "15-minute quotes long enough for V1 (V1 is judged only if they are)", "A16"),
    StopRuleInput(
        "B",
        "shadow strategies registered in the ledger with pass mark and minimum useful net",
        "R1",
        GATES_FILE,
        _shadows_registered,
    ),
    StopRuleInput("B", "resolved shadow trades, net after costs", "R3", SHADOW_ACCOUNTS),  # each account in Drive (E2c)
)


@dataclass(frozen=True)
class ReviewDate:
    day: date
    basis: str
    notes: tuple[str, ...]


def review_date(freeze: date | None, projected_month: str, sessions: SessionCalendar) -> ReviewDate:
    start = freeze or date.fromisoformat(projected_month + "-01")
    year, month = divmod(start.month - 1 + FULL_MONTHS, 12)
    last = _last_session(start.year + year, month + 1, sessions)
    basis = DECIDED.format(day=freeze) if freeze else PROJECTED.format(month=f"{start:%B %Y}")
    return ReviewDate(last[0], basis, last[1])


def _last_session(year: int, month: int, sessions: SessionCalendar) -> tuple[date, tuple[str, ...]]:
    day = date(year, month, calendar.monthrange(year, month)[1])
    try:
        while not sessions.is_session(day):
            day -= timedelta(1)
        return day, ()
    except CalendarError:
        while day.weekday() >= 5:
            day -= timedelta(1)
        return day, (WEEKDAY_FALLBACK.format(year=year),)


def stop_test_status(root: Path, test: str) -> tuple[str, list[StopRuleInput]]:
    """'computable' or 'not computable yet', with the inputs still missing."""
    missing = [i for i in INPUTS if i.test == test and not i.exists(root)]
    return ("computable" if not missing else NOT_COMPUTABLE), missing


def review_reached(review: ReviewDate, today: date) -> str:
    """Design v2 section 6.5's SYSTEM alert "a stop-rule date reached", or empty before the date. A date that rests on a
    fallback says so in the alert itself (A7: every calendar user fails loudly, by name, never silently)."""
    if today < review.day:
        return ""
    alert = REVIEW_REACHED.format(day=review.day, basis=review.basis)
    return alert + UNCONFIRMED.format(notes="; ".join(review.notes)) if review.notes else alert
