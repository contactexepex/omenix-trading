"""Each v4 day's quality label (story G10, protocol section 1.6), as G8 reads it. The release run writes one record per
scored session, Drive `v4/days/<YYYY>/<YYYY-MM-DD>.json`: the label (`A` the 14:30 live capture, `system_late` no
complete pack by 14:40 or no release record at all), the released pack's SHA-256 and the pack's latest `observed_at`.
A `system_late` day is out for every family (`LateDaysOut`) and counted; the "moved after cutoff" flag is counted,
never a reason to drop a day. A day with no record has the label `missing_label` gives it (G10 completion, criterion
5, one rule for the writer and every reader): before the live date none (the close-proxy cohort), a live day before
the report's date `system_late`, the report's own date pending."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from ...constants import V4_DAY_A, V4_DAY_SYSTEM_LATE
from ...forecast_v4.terms import V4_PACK_WINDOW_END
from ...models import IST
from .inputs import ForecastValue, Outcome, V4ForecastSource, V4OutcomeSource

LABELS = (V4_DAY_A, V4_DAY_SYSTEM_LATE)  # A2 (A16's mark as fallback) dropped: it cannot hold a full pack
SHA256 = re.compile(r"[0-9a-f]{64}")
PENDING = "pending"  # the report's own date with no release record yet: never scored, counted apart
COUNTS_LINE = ("days (live pack): A {a}, system_late {late} (out for every family), pending {pending}; moved after "
               "cutoff {flagged}, flag not computable {unknown}; deadline not checked {unchecked}")  # fmt: skip


class DayFileError(ValueError):
    """A day file that breaks the format: scoring stops rather than guess a day's label."""


@dataclass(frozen=True)
class DayLabel:
    day: date
    label: str
    pack_sha256: str  # "" only on a system_late day with no pack
    observed_by: datetime | None  # the pack's latest observed_at; None only on a system_late day with no pack


@dataclass(frozen=True)
class DayCounts:
    a: int
    late: int
    flagged: int
    unknown: int  # labelled days whose 14:30 or 15:15 level is missing: the flag is not computable
    pending: int = 0  # the report's own date, its release record not written yet
    unchecked: int = 0  # live days with a row whose 15:10 deadline has no verdict yet (G10 completion, criterion 8)

    def line(self) -> str:
        return COUNTS_LINE.format(a=self.a, late=self.late, pending=self.pending, flagged=self.flagged,
                                  unknown=self.unknown, unchecked=self.unchecked)  # fmt: skip


class V4DaySource(ABC):
    @abstractmethod
    def labels(self) -> dict[date, DayLabel]:
        """One entry per labelled day."""


def parse_day(stem: str, body: dict) -> DayLabel:
    day = date.fromisoformat(stem)
    if body.get("day") != stem or body.get("label") not in LABELS:
        raise DayFileError(f"{stem}: the day or the label is not valid")
    sha, observed = body.get("pack_sha256") or "", body.get("observed_by") or ""
    observed_by = datetime.fromisoformat(observed) if observed else None
    if sha and not SHA256.fullmatch(sha):
        raise DayFileError(f"{stem}: the pack's SHA-256 is not valid")
    if body["label"] == V4_DAY_SYSTEM_LATE:
        return DayLabel(day, body["label"], sha, observed_by)
    if not sha or observed_by is None:
        raise DayFileError(f"{stem}: an {body['label']} day names its pack's SHA-256 and its latest observed_at")
    if observed_by > datetime.combine(day, V4_PACK_WINDOW_END, IST):
        raise DayFileError(f"{stem}: a field observed after {V4_PACK_WINDOW_END:%H:%M} makes the day system_late")
    return DayLabel(day, body["label"], sha, observed_by)


def missing_label(day: date, live_from: date | None, today: date) -> str | None:
    """The label of a scored session with no release record: none before the live date (the close-proxy cohort),
    `system_late` for a live day before `today` (no release record at all, protocol 1.6), `PENDING` on `today`."""
    if live_from is None or day < live_from:
        return None
    return V4_DAY_SYSTEM_LATE if day < today else PENDING


def day_counts(labels: dict[date, DayLabel], moved: Callable[[date], bool | None], as_of: date,
               pending: int = 0, unchecked: int = 0) -> DayCounts:  # fmt: skip
    """`moved(d)`: whether day d moved after the cutoff (None: not computable)."""
    shown = [label for day, label in labels.items() if day <= as_of]
    flags = [moved(label.day) for label in shown]
    count = [label.label for label in shown].count
    return DayCounts(count(V4_DAY_A), count(V4_DAY_SYSTEM_LATE), flags.count(True), flags.count(None), pending,
                     unchecked)  # fmt: skip


class LiveDayLabels(V4DaySource):
    """The release records plus `missing_label`'s answer for every scored session without one, so a day the release
    run never settled is `system_late` here too (the writer's catch-up and this reader keep one rule)."""

    def __init__(self, records: V4DaySource, sessions: Callable[[date, date], list[date]], live_from: date | None,
                 today: date):  # fmt: skip
        """`sessions(a, b)`: the scored sessions in [a, b]."""
        self.records, self.sessions, self.live_from, self.today = records, sessions, live_from, today

    def labels(self) -> dict[date, DayLabel]:
        """A stored record dated before the live date is ignored (judge 613: a rehearsal's record that reached the
        receipts can never drop a day the real report keeps); with the pack not live, no day has a label."""
        if self.live_from is None:
            return {}
        found = {d: label for d, label in self.records.labels().items() if d >= self.live_from}
        if self.today <= self.live_from:
            return found
        missing = [d for d in self.sessions(self.live_from, self.today - timedelta(days=1)) if d not in found]
        return {**found, **{d: DayLabel(d, V4_DAY_SYSTEM_LATE, "", None) for d in missing}}

    def pending(self) -> int:
        """1 when the report's own date is a live scored session with no release record yet, else 0."""
        if missing_label(self.today, self.live_from, self.today) != PENDING:
            return 0
        return int(bool(self.sessions(self.today, self.today)) and self.today not in self.records.labels())


class LateDaysOut(V4ForecastSource, V4OutcomeSource):
    """The forecasts and outcomes without the `system_late` days: with no pack, no family had the same inputs, so
    the day is neither scored nor a miss for anyone (protocol section 4)."""

    def __init__(self, forecasts: V4ForecastSource, outcomes: V4OutcomeSource, days: V4DaySource):
        self.forecast_source, self.outcome_source, self.days = forecasts, outcomes, days

    def forecasters(self, question: str) -> list[str]:
        return self.forecast_source.forecasters(question)

    def values(self, question: str, forecaster: str) -> dict[date, ForecastValue]:
        return self._without_late(self.forecast_source.values(question, forecaster))

    def outcomes(self, question: str) -> dict[date, Outcome]:
        return self._without_late(self.outcome_source.outcomes(question))

    def _without_late(self, by_day: dict) -> dict:
        late = {d for d, label in self.days.labels().items() if label.label == V4_DAY_SYSTEM_LATE}
        return {d: v for d, v in by_day.items() if d not in late}
