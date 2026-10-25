"""What each edition's report is made of (story FL1-1d). The evening: FL1-1's seal checks and matches (its alerts and
coverage) and the page with today's check. The morning: the page with today's forecast, and the confirmation of the
earlier evenings' checks against the official closes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from .confirm import Confirmation
from .constants import EVENING, MORNING
from .edition_run import Composer
from .maker import ReportMaker
from .report import CloseReport
from .written import WrittenReport


class EveningComposer(Composer):
    def __init__(self, report: CloseReport, maker: ReportMaker, earlier: Callable[[date], WrittenReport | None]):
        """`earlier`: the earlier evenings' records (what they covered)."""
        self.report, self.maker, self.earlier = report, maker, earlier

    def compose(self, day: date, now: datetime) -> WrittenReport:
        checked = self.report.build(day, now, self.earlier)
        made = self.maker.make(day, now, EVENING, checked.alerts, checked.text)
        return WrittenReport(made.text, checked.alerts + made.alerts, checked.checked, checked.matched, made.files,
                             made.verdicts)  # fmt: skip


class MorningComposer(Composer):
    def __init__(self, maker: ReportMaker, confirmation: Confirmation):
        self.maker, self.confirmation = maker, confirmation

    def compose(self, day: date, now: datetime) -> WrittenReport:
        confirmed = self.confirmation.confirm(day)
        made = self.maker.make(day, now, MORNING, confirmed.alerts, confirmation=confirmed.lines)
        return WrittenReport(made.text, confirmed.alerts + made.alerts, matched=confirmed.keys, attachments=made.files)
