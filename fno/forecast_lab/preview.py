"""The owner's preview of an edition (owner, 23 Oct 2026, through the orchestrator: "do a dry run again, publish
both the reports ... I want to see how it will look like ... Don't change the numbers for morning forecast"): the
edition's own composer with today's code, posted once to #fno-forecast under a bold first line saying it is a dry
run. It writes nothing: no record, no posted or alerted marker, no receipt, no commit (only `EditionRun` writes, and
the preview never builds one), and it sends no alert (its alerts are printed). A morning preview is posted only when
every range of the sealed morning record appears unchanged in it."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, datetime

from .constants import MORNING
from .delivery import ReportPoster
from .edition_run import Composer
from .written import WrittenReport

LABEL = "*DRY RUN (owner's preview, {day:%d %b}): not today's report; the official editions are above*"
RANGES = re.compile(r"most likely [\d,]+–[\d,]+ \(almost certainly [\d,]+–[\d,]+\)")
NO_RECORD = "lab preview {day}: no sealed morning record to keep the numbers of; not posted"
CHANGED = "lab preview {day}: the morning's ranges differ from its sealed record ({missing}); not posted"
POSTED = "lab preview {day} {edition}: {outcome}"
ALERT = "lab preview {day}: would alert: {alert}"


def same_ranges(sealed: str, preview: str) -> list[str]:
    """The sealed text's ranges missing from the preview (empty: the numbers are unchanged)."""
    return [r for r in RANGES.findall(sealed) if r not in preview]


class Preview:
    def __init__(self, composer: Composer, poster: ReportPoster, sealed: Callable[[date], WrittenReport | None]):
        """`sealed(day)`: the edition's own written record of that day (read-only)."""
        self.composer, self.poster, self.sealed = composer, poster, sealed

    def run(self, edition: str, day: date, now: datetime) -> tuple[list[str], bool]:
        """(the lines to print, whether it was posted)."""
        written = self.composer.compose(day, now)
        if edition == MORNING:
            record = self.sealed(day)
            if record is None:
                return [NO_RECORD.format(day=day)], False
            missing = same_ranges(record.text, written.text)
            if missing:
                return [CHANGED.format(day=day, missing="; ".join(missing))], False
        delivery = self.poster.post(f"{LABEL.format(day=day)}\n{written.text}", list(written.attachments))
        alerts = [ALERT.format(day=day, alert=alert) for alert in written.alerts]
        return [POSTED.format(day=day, edition=edition, outcome=delivery.outcome), *alerts], delivery.sent
