"""The recommender's sections in the 08:50 and 20:05 editions (story REC1d). The morning shows the standing real-money
answer from the latest recommendation before today, then the checks made on the previous NSE session, each dated;
a day still waiting with no check dated that session is named. The evening shows today's two answers and says that
tonight's check comes after it. Each reads only receipted records through its ports; an unreadable record or check is
named by path and exception class, and never fails the edition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date

from ..school.contracts.seal import StaleSeal
from .check_record import FINAL, CheckRecord, Verdict
from .check_run import parse_check
from .check_text import answer_text, trades_text
from .codec import decode
from .contracts import Recommendation
from .post import paper_text, real_money_text
from .report_words import (
    CHECK,
    CHECK_NOT_READ,
    NO_CHECKS,
    NO_RECORD,
    NO_RECORD_STEP,
    NO_VERSIONS,
    NOT_DATED,
    NOT_KNOWN,
    NOT_READ,
    NOTHING_YET,
    RUNG,
    RUNGS,
    STANDING,
    TONIGHT,
    shown_problem,
)  # fmt: skip
from .shelf import ReceiptShelf, check_path
from .store import record_path

READ_FAILURES = (StaleSeal, OSError, ValueError, KeyError)  # RecordRefused is a ValueError


class Unread(Exception):
    def __init__(self, path: str, failed: Exception):
        super().__init__(path)
        self.path, self.kind = path, type(failed).__name__


@dataclass(frozen=True)
class ReportPorts:
    shelf: ReceiptShelf
    read: Callable[[str], bytes]  # a data-area file, verified against its receipt
    previous_session: Callable[[date], date | None]  # the NSE session before a day
    step: Callable[[date], tuple[str, str] | None]  # the run log's `recommend` (status, reason), if it ran


class Records:
    """The receipted records, read and decoded; a failure is `Unread`, naming the path and the exception class."""

    def __init__(self, ports: ReportPorts):
        self.ports = ports

    def recommendation(self, day: date) -> Recommendation:
        return self._read(record_path(day), decode)

    def check(self, day: date, on: date) -> CheckRecord:
        return self._read(check_path(day, on), parse_check)

    def _read(self, path: str, parse):
        try:
            return parse(self.ports.read(path))
        except READ_FAILURES as failed:
            raise Unread(path, failed) from None


class MorningSection:
    def __init__(self, ports: ReportPorts):
        self.ports, self.records = ports, Records(ports)

    def render(self, today: date) -> tuple[str, ...]:
        days = [d for d in self.ports.shelf.recorded_days(today) if d < today]  # today's answer comes at 15:20
        if not days:
            return (NOTHING_YET,)
        previous = self.ports.previous_session(today)
        return (*self._standing(days[-1]), *(self._checks(days, previous) if previous else ()))

    def _standing(self, day: date) -> tuple[str, ...]:
        try:
            record = self.records.recommendation(day)
        except Unread as unread:
            return (NOT_READ.format(day=day, path=unread.path, kind=unread.kind),)
        rungs = "; ".join(RUNG.format(version=v.version, rung=int(v.rung), name=v.rung.name.lower())
                          for v in record.versions)  # fmt: skip
        return STANDING.format(day=day), real_money_text(record), RUNGS.format(rungs=rungs) if rungs else NO_VERSIONS

    def _checks(self, days: list[date], previous: date) -> list[str]:
        """Only the checks dated the previous session: an older one is never shown (judge 664 SF2)."""
        lines, waiting = [], []
        for day in (d for d in days if d <= previous):
            made = self.ports.shelf.checks(day, previous)
            try:
                if made and made[-1] == previous:
                    lines.append(self._check_line(day, previous))
                elif not made or self.records.check(day, made[-1]).verdict not in FINAL:
                    waiting.append(day)
            except Unread as unread:
                lines.append(CHECK_NOT_READ.format(day=day, on=previous, path=unread.path, kind=unread.kind))
        if waiting:
            lines.append(NOT_DATED.format(on=previous, days=", ".join(f"{d:%d %b %Y}" for d in waiting)))
        return lines or [NO_CHECKS.format(on=previous)]

    def _check_line(self, day: date, on: date) -> str:
        check = self.records.check(day, on)
        return CHECK.format(day=day, on=on, verdict=check.verdict.value.replace("_", " "),
                            answer=self._answer(day, on, check), trades=trades_text(check))  # fmt: skip

    def _answer(self, day: date, on: date, check: CheckRecord) -> str:
        """A day not final yet has no answer, only its open count; a failed one needs no record (it may be the
        unread one) and shows its problem only through the words guard."""
        if check.verdict not in FINAL:
            return NOT_KNOWN.format(open=check.open_positions)
        if check.verdict is Verdict.DATA_CHECK_FAILED:
            return answer_text(None, replace(check, problem=shown_problem(check.problem, check_path(day, on))))
        return answer_text(self.records.recommendation(day), check)


class EveningSection:
    def __init__(self, ports: ReportPorts):
        self.ports, self.records = ports, Records(ports)

    def render(self, today: date) -> tuple[str, ...]:
        if today not in self.ports.shelf.recorded_days(today):
            step = self.ports.step(today)  # its status and reason code only, never its printed lines (judge 664 m1)
            return (NO_RECORD.format(day=today) if step is None
                    else NO_RECORD_STEP.format(day=today, status=step[0], reason=step[1]),)  # fmt: skip
        try:
            record = self.records.recommendation(today)
        except Unread as unread:
            return NOT_READ.format(day=today, path=unread.path, kind=unread.kind), TONIGHT
        return real_money_text(record), paper_text(record), TONIGHT
