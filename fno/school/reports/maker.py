"""The school's sections in an edition's message (story MS-P1g): wraps the report maker and, when `school.reports` is
on, appends the edition's section to its text (08:50 "Today", 20:05 "How did today go"). The picture and the details
file are the signed-off page, untouched. A section that fails never stops the edition: one alert names the failure."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import date, datetime

from ...forecast_lab.maker import Made
from ..contracts.reports import ReportSection

SECTION_FAILED = "school {edition} section not made ({failure}); the edition was posted without it"


def failure_alert(edition: str, failed: Exception) -> str:
    """The exception's class and a fixed text, never its message: no strike or value can reach #fno-desk."""
    return SECTION_FAILED.format(edition=edition, failure=type(failed).__name__)


class SchoolReportMaker:
    def __init__(self, inner, sections: Mapping[str, ReportSection]):
        self.inner, self.sections = inner, sections

    def make(self, day: date, now: datetime, edition: str, alerts: tuple[str, ...] = (), checks: str = "",
             confirmation: tuple[str, ...] = ()) -> Made:  # fmt: skip
        made = self.inner.make(day, now, edition, alerts, checks, confirmation)
        section = self.sections.get(edition)
        if section is None:
            return made
        try:
            text = section.render(day)
        except Exception as failed:  # isolation: the school never stops an edition
            return replace(made, alerts=(*made.alerts, failure_alert(edition, failed)))
        block = "\n".join((text.title, *text.lines))
        return replace(made, text=f"{made.text}\n\n{block}")


class FailedSchoolMaker:
    """The plain edition with one alert, when the school could not even be set up (settings, import)."""

    def __init__(self, inner, failed: Exception):
        self.inner, self.failed = inner, failed

    def make(self, day: date, now: datetime, edition: str, alerts: tuple[str, ...] = (), checks: str = "",
             confirmation: tuple[str, ...] = ()) -> Made:  # fmt: skip
        made = self.inner.make(day, now, edition, alerts, checks, confirmation)
        return replace(made, alerts=(*made.alerts, failure_alert(edition, self.failed)))
