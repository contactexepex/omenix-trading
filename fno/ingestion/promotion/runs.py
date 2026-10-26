"""The two daily passes over a range of sessions: the stager (a source into Staging, nothing else) and the promotion
run (Staging through the gate into the Record). Both walk the same sessions as the librarian: the NSE calendar's, minus
the sourced exceptions, within the dataset's archive range."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from fno.ingestion.promotion.gate import Promotion, PromotionGate, Verdict
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.research_data.calendar import SessionCalendar
from fno.ingestion.storage.coverage import archive_range, days_between
from fno.ingestion.storage.raw_source import NseArchiveSource, RawFileRefused
from fno.shared.models import now_utc


def session_days(
    source: type[NseArchiveSource], calendar: SessionCalendar, start: date | None, end: date
) -> list[date]:
    start, end = archive_range(source, start, end)
    return [day for day in days_between(start, end) if calendar.is_session(day)]


@dataclass
class StageReport:
    dataset: str
    staged: list[date] = field(default_factory=list)
    unchanged: list[date] = field(default_factory=list)  # the newest staged copy already has these bytes
    not_published: list[date] = field(default_factory=list)
    refused: list[tuple[date, str]] = field(default_factory=list)
    excepted: int = 0

    @property
    def complete(self) -> bool:
        return not (self.not_published or self.refused)

    def lines(self) -> list[str]:
        head = (
            f"{self.dataset}: staged {len(self.staged)}, unchanged {len(self.unchanged)}, "
            f"{self.excepted} with a sourced exception"
        )
        lines = [f"not published by the source {day}" for day in self.not_published]
        lines += [f"source refused {day}: {reason}" for day, reason in self.refused]
        return [head, *lines, f"result: {'complete' if self.complete else 'INCOMPLETE: see the lines above'}"]


class Stager:
    def __init__(self, source: NseArchiveSource, staging: StagingArea, tag: str, calendar: SessionCalendar,
                 exceptions: dict[tuple[str, date], str], clock: Callable[[], datetime] = now_utc):  # fmt: skip
        self.source, self.staging, self.tag = source, staging, tag
        self.calendar, self.exceptions, self.clock = calendar, exceptions, clock

    def stage(self, start: date | None, end: date) -> StageReport:
        report = StageReport(self.source.dataset)
        for day in session_days(type(self.source), self.calendar, start, end):
            if (self.source.dataset, day) in self.exceptions:
                report.excepted += 1
                continue
            self._stage_day(day, report)
        return report

    def _stage_day(self, day: date, report: StageReport) -> None:
        path = self.source.path_for(day)
        try:
            data = self.source.fetch(path)
        except RawFileRefused as exc:  # this one file only; any other failure stops the pass (RawSourceUnavailable)
            report.refused.append((day, str(exc)))
            return
        if data is None:
            report.not_published.append(day)
        elif self.staging.stage(self.tag, path, data, self.clock()):
            report.staged.append(day)
        else:
            report.unchanged.append(day)


DONE = (Verdict.PROMOTED, Verdict.ALREADY_RECORDED)  # the Record holds the file


def _problem_line(day: date, result: Promotion) -> str:
    reasons = f": {'; '.join(result.reasons)}" if result.reasons else ""
    return f"{result.verdict.value} {day}{reasons}"


@dataclass
class PromotionReport:
    dataset: str
    results: list[tuple[date, Promotion]] = field(default_factory=list)
    excepted: int = 0

    def days(self, verdict: Verdict) -> list[date]:
        return [day for day, result in self.results if result.verdict is verdict]

    @property
    def complete(self) -> bool:
        return all(r.verdict in DONE for _, r in self.results)

    def problems(self) -> list[str]:
        return [_problem_line(day, r) for day, r in self.results if r.verdict not in DONE]

    def lines(self) -> list[str]:
        counts = ", ".join(f"{len(self.days(v))} {v.value}" for v in Verdict)
        verdict = "complete" if self.complete else "INCOMPLETE: see the lines above"
        return [f"{self.dataset}: {counts}, {self.excepted} with a sourced exception", *self.problems(),
                f"result: {verdict}"]  # fmt: skip


class PromotionRun:
    def __init__(self, gate: PromotionGate, source: type[NseArchiveSource], calendar: SessionCalendar,
                 exceptions: dict[tuple[str, date], str]):  # fmt: skip
        self.gate, self.source, self.calendar, self.exceptions = gate, source, calendar, exceptions

    def promote(self, start: date | None, end: date) -> PromotionReport:
        report = PromotionReport(self.source.dataset)
        for day in session_days(self.source, self.calendar, start, end):
            if (self.source.dataset, day) in self.exceptions:
                report.excepted += 1
                continue
            result = self.gate.promote(self.source.path_for(day), day, self.source.filename_for(day))
            report.results.append((day, result))
        return report
