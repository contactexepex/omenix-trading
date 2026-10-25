"""`lab open` and `lab close` (stories FL1-1 and FL1-1d): one edition's report, written once, posted once to
#fno-forecast, its alerts sent once to #fno-desk. A rerun after the report was written posts the stored text and
alerts, never rebuilt ones (scores may have moved since). Each step has its own write-once marker (judge 422): a
rerun after the post sends no second post, and a rerun after the alerts sends no second alert. The alerts' marker is
written after the sends (a crash in between sends them again rather than losing them). Every alert's outcome is
printed, an unsent one with its text so the routine posts it by hand. A report not posted is the run's failure (exit
1), and the run alerts it once itself with that day's alerts: the editions run from the owner's routines, outside O1's
`Alerted`. A post Slack may have made without answering is never retried (no double post), so it is marked posted and
the failure says to check the channel. The morning edition is today's forecast only before the open: at or after 09:15
it is not posted, and one alert says so (owner, DESK_DECISIONS line 284); the cutoff is checked again just before
the post, since making the report takes time. Any failure before the post (a Drive sync refused while the edition is
built, a report that cannot be made) is alerted once by `guarded`, never silent (judge 444)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time

from ..alerts.sender import SENT, AlertSender
from .constants import (
    ALERT,
    ALERTS_ALREADY,
    ALERTS_SENT,
    ALREADY_POSTED,
    CHECK_BEFORE_REPOST,
    COMMANDS,
    CRASHED,
    LATE_ALERT,
    NOT_A_SESSION,
    NOT_LIVE,
    NOT_POSTED,
    REPORT_ALREADY,
    REPORT_POSTED,
    TOO_LATE,
)
from .delivery import ReportPoster
from .written import WrittenReport


class ReportRecords(ABC):
    """One edition's write-once records (O9: Drive data area, one receipt each)."""

    @abstractmethod
    def report(self, day: date) -> WrittenReport | None:
        """The day's report as written, or None."""

    @abstractmethod
    def write_report(self, day: date, report: WrittenReport) -> None: ...

    @abstractmethod
    def posted(self, day: date) -> bool: ...

    @abstractmethod
    def mark_posted(self, day: date, outcome: str) -> None: ...

    @abstractmethod
    def alerted(self, day: date) -> bool: ...

    @abstractmethod
    def mark_alerted(self, day: date, outcomes: list[str]) -> None: ...


@dataclass(frozen=True)
class LabResult:
    lines: list[str]
    failed: bool = False


class Composer(ABC):
    """Makes one edition's report: its text, files, alerts and what it covered."""

    @abstractmethod
    def compose(self, day: date, now: datetime) -> WrittenReport: ...


@dataclass(frozen=True)
class Edition:
    name: str  # "morning" or "evening"
    live_from: date | None  # the edition's first live day (config); None: not live
    post_before: time | None = None  # the morning's 09:15: no post at or after it


class EditionRun:
    def __init__(self, edition: Edition, composer: Composer, records: ReportRecords, poster: ReportPoster,
                 desk: AlertSender, is_regular: Callable[[date], bool], clock: Callable[[], datetime]):  # fmt: skip
        self.edition, self.composer, self.records, self.poster, self.desk = edition, composer, records, poster, desk
        self.is_regular, self.clock, self.name = is_regular, clock, COMMANDS[edition.name]

    def run(self, day: date) -> LabResult:
        live_from = self.edition.live_from
        if live_from is None or day < live_from:
            return LabResult([NOT_LIVE.format(name=self.name, day=day, edition=self.edition.name, since=live_from)])
        if not self.is_regular(day):
            return LabResult([NOT_A_SESSION.format(name=self.name, day=day)])
        posted, alerted = self.records.posted(day), self.records.alerted(day)
        if posted and alerted:
            return LabResult([ALREADY_POSTED.format(name=self.name, day=day)])
        if not posted and self._too_late():
            return self._late(day, alerted)
        written = self.records.report(day)
        if written is None:
            written = self.composer.compose(day, self.clock())
            self.records.write_report(day, written)
        if not posted and self._too_late():  # making it took time: the open may have come meanwhile
            return self._late(day, alerted, written.alerts)
        lines, problem = [REPORT_ALREADY.format(name=self.name, day=day)], None
        if not posted:
            lines, problem = self._post(day, written)
        alerts = written.alerts + ((problem,) if problem else ())
        lines += [ALERTS_ALREADY.format(name=self.name, day=day)] if alerted else self._alert(day, alerts)
        return LabResult(lines, problem is not None)

    def _too_late(self) -> bool:
        cutoff = self.edition.post_before
        return cutoff is not None and self.clock().time() >= cutoff

    def _late(self, day: date, alerted: bool, report_alerts: tuple[str, ...] = ()) -> LabResult:
        """Not posted after the cutoff: the late alert, with the report's own alerts when it was made (a CORRECTION
        is never dropped because the morning ran late: judge 444.1)."""
        now = self.clock()
        lines = [TOO_LATE.format(name=self.name, day=day, now=now)]
        if alerted:
            return LabResult(lines + [ALERTS_ALREADY.format(name=self.name, day=day)], True)
        return LabResult(lines + self._alert(day, (*report_alerts, LATE_ALERT.format(now=now))), True)

    def _post(self, day: date, written: WrittenReport) -> tuple[list[str], str | None]:
        """(the lines, the failure to alert, or None when it was posted)."""
        delivery = self.poster.post(written.text, list(written.attachments))
        if delivery.sent or delivery.may_have_posted:
            self.records.mark_posted(day, delivery.outcome)
        line = REPORT_POSTED.format(name=self.name, day=day, outcome="posted" if delivery.sent else delivery.outcome)
        if delivery.sent:
            return [line], None
        tail = CHECK_BEFORE_REPOST if delivery.may_have_posted else ""
        problem = NOT_POSTED.format(edition=self.edition.name, outcome=delivery.outcome) + tail
        return [line, problem], problem

    def _alert(self, day: date, alerts: tuple[str, ...]) -> list[str]:
        texts = [ALERT.format(day=day, what=what) for what in alerts]
        outcomes = [self.desk.send(text) for text in texts]
        self.records.mark_alerted(day, outcomes)
        unsent = [f"{outcome}: {text}" for outcome, text in zip(outcomes, texts, strict=True) if outcome != SENT]
        return [ALERTS_SENT.format(name=self.name, day=day, sent=len(texts) - len(unsent), total=len(texts)), *unsent]


def guarded(edition: str, day: date, build: Callable[[], EditionRun], desk: AlertSender) -> LabResult:
    """Builds and runs the edition; any failure before its own handling (a Drive sync refused, a report that cannot be
    made) is one #fno-desk alert with the edition, the day and the error's type, and the run's failure (exit 1). The
    alert's outcome is printed, an unsent one with its text, for the routine to post by hand."""
    try:
        return build().run(day)
    except Exception as error:  # noqa: BLE001  outside O1's Alerted: nothing may fail silently
        what = CRASHED.format(edition=edition, error=type(error).__name__)
        text = ALERT.format(day=day, what=what)
        outcome = desk.send(text)
        lines = [f"{COMMANDS[edition]} {day}: {what}"]
        return LabResult(lines + ([] if outcome == SENT else [f"{outcome}: {text}"]), True)
