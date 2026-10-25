"""Scheduled market events (story A6): RBI policy decisions, Union Budgets, general-election results.

`research/data/events/events.csv` holds every event with official sources and the date its date was publicly
announced. The experiment may only use what a trader could know on its decision day (`known_on`):
- a scheduled event from its announcement date;
- a rescheduled event at its ORIGINAL date from the first announcement until the reschedule was announced (or, for an
  unscheduled event that replaced a scheduled meeting, until the event happened), so a known meeting never vanishes;
- unscheduled events (e.g. an emergency RBI decision) are kept for the record but never usable ahead.
Announcement dates are late bounds: never look-ahead, but they may treat an event as unknown for a few extra days.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from ..models import today_local

COLUMNS = (
    "date", "type", "scheduled", "announced_on", "announcement_source_url", "revised_from", "description", "source_url",
    "first_announced_on", "first_announcement_source_url", "first_withdrawn_on",
)  # fmt: skip
TYPES = ("rbi_policy", "budget", "election_result")
OFFICIAL_HOSTS = (
    "rbi.org.in",
    "pib.gov.in",
    "indiabudget.gov.in",
    "eci.gov.in",
)  # story A6 criterion 1 (and subdomains)
YES, NO = "yes", "no"


@dataclass(frozen=True)
class Event:
    day: date
    kind: str
    scheduled: bool
    announced_on: date | None
    description: str
    revised_from: date | None = None  # the original date, when the event was moved
    first_announced_on: date | None = None  # when the original date was announced
    first_withdrawn_on: date | None = None  # when the original date was withdrawn, if before the new one was announced

    def as_originally_known(self) -> Event:
        """The event as traders knew it before the move: at its original date."""
        note = f"as first announced (moved to {self.day} later): {self.description}"
        return Event(self.revised_from, self.kind, True, self.first_announced_on, note)


def _iso(text: str, row: int, column: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"row {row}: bad {column} {text!r}") from exc


def _official(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return url.startswith("https://") and any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS)


def _optional_iso(text: str, row: int, column: str) -> date | None:
    return _iso(text, row, column) if text else None


def read_events(text: str, today: date | None = None) -> list[Event]:
    """Validated events; any bad row raises with its row number (nothing is read partly). An event dated after
    `today` (an upcoming, already announced meeting) may lack the source confirming it happened, never its
    announcement source."""
    today = today or today_local()
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError(f"events columns must be {COLUMNS}")
    events = []
    for number, row in enumerate(reader, start=2):
        if row["type"] not in TYPES:
            raise ValueError(f"row {number}: unknown type {row['type']!r}")
        if row["scheduled"] not in (YES, NO):
            raise ValueError(f"row {number}: scheduled must be yes or no")
        day = _iso(row["date"], number, "date")
        if day <= today and not _official(row["source_url"]):
            raise ValueError(f"row {number}: source must be an official https page ({', '.join(OFFICIAL_HOSTS)})")
        scheduled = row["scheduled"] == YES
        announced = _optional_iso(row["announced_on"], number, "announced_on")
        if scheduled:
            if announced is None or not row["announcement_source_url"].startswith("http"):
                raise ValueError(f"row {number}: a scheduled event needs its announcement date and source")
            if announced >= day:
                raise ValueError(f"row {number}: announced on {announced}, not before the event on {day}")
        revised = _optional_iso(row["revised_from"], number, "revised_from")
        first = _optional_iso(row["first_announced_on"], number, "first_announced_on")
        if first is not None:
            if revised is None or first >= revised or not row["first_announcement_source_url"].startswith("https://"):
                raise ValueError(f"row {number}: a first announcement needs revised_from after it and an https source")
            if announced is not None and first > announced:
                raise ValueError(f"row {number}: first announced on {first}, after the revision on {announced}")
        withdrawn = _optional_iso(row["first_withdrawn_on"], number, "first_withdrawn_on")
        if withdrawn is not None and (first is None or not first < withdrawn <= day):
            raise ValueError(f"row {number}: first_withdrawn_on needs a first announcement before it")
        events.append(Event(day, row["type"], scheduled, announced, row["description"], revised, first, withdrawn))
    return sorted(events, key=lambda e: (e.day, e.kind))


def known_on(events: list[Event], decision_day: date) -> list[Event]:
    """Events a trader could have known about on the decision day, each at the date known then (see module doc)."""
    known = []
    for event in events:
        if event.scheduled and event.announced_on is not None and event.announced_on <= decision_day:
            known.append(event)
        elif event.first_announced_on is not None and event.first_announced_on <= decision_day < _move_known(event):
            known.append(event.as_originally_known())
    return sorted(known, key=lambda e: (e.day, e.kind))


def _move_known(event: Event) -> date:
    """The day the original date stopped being known: its withdrawal, else the move's announcement, else (for an
    unscheduled event that replaced a meeting) the event itself."""
    if event.first_withdrawn_on is not None:
        return event.first_withdrawn_on
    return event.announced_on if event.scheduled and event.announced_on is not None else event.day


def in_window(events: list[Event], decision_day: date, start: date, end: date) -> list[Event]:
    """Known events dated after `start` and on or before `end` (the holding window)."""
    return [e for e in known_on(events, decision_day) if start < e.day <= end]
