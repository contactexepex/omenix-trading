"""The recommender's block in an edition's message (story REC1d, items 1-3): a wrapper of its own around the lab's
maker (outside the school's), so only `daily.live_from.recommend` decides whether it shows. The inner maker's text,
files and alerts are kept as made; the block is appended after them, and a section that fails gives one alert naming
the edition and the exception class, never its message, and never removes what the inner maker made."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from .report_words import SECTION_FAILED, TITLE


def failure_alert(edition: str, failed: Exception) -> str:
    return SECTION_FAILED.format(edition=edition, failure=type(failed).__name__)


class RecommendReportMaker:
    def __init__(self, inner, sections: dict, live_from: date):
        """`sections`: edition -> a section with `render(day) -> lines`; shown on days from `live_from`."""
        self.inner, self.sections, self.live_from = inner, sections, live_from

    def make(self, day: date, now: datetime, edition: str, alerts: tuple[str, ...] = (), checks: str = "",
             confirmation: tuple[str, ...] = ()):  # fmt: skip
        made = self.inner.make(day, now, edition, alerts, checks, confirmation)
        section = self.sections.get(edition)
        if section is None or day < self.live_from:
            return made
        try:
            lines = section.render(day)
        except Exception as failed:  # isolation: the recommender never stops an edition or the school's section
            return replace(made, alerts=(*made.alerts, failure_alert(edition, failed)))
        return replace(made, text=f"{made.text}\n\n" + "\n".join((TITLE, *lines)))


class FailedRecommendMaker:
    """The inner edition with one alert, when the recommender's block could not even be set up."""

    def __init__(self, inner, failed: Exception):
        self.inner, self.failed = inner, failed

    def make(self, day: date, now: datetime, edition: str, alerts: tuple[str, ...] = (), checks: str = "",
             confirmation: tuple[str, ...] = ()):  # fmt: skip
        made = self.inner.make(day, now, edition, alerts, checks, confirmation)
        return replace(made, alerts=(*made.alerts, failure_alert(edition, self.failed)))
