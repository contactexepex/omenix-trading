"""Confirms each earlier provisional close against NSE's official file, once (a write-once `.confirm.json`): within
0.01 point "confirmed", else "differs by X" and one #fno-desk alert for NIFTY 50 or NIFTY BANK (INDIA VIX is the
list's value: its difference is recorded only). From A4h-2 the day's high and low are confirmed against the same file
and the previous close against the previous session's file; a record without them is confirmed on `last` alone. A day
still unconfirmed at the second session after it alerts once. A day that fails (the archive or Drive unreachable, a
damaged file) prints one line with the error's class only and stays unconfirmed; it never alerts on its own, and the
overdue rule still applies to it (judge 447 SF1)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime, timedelta

from ..alerts.output import announce
from ..alerts.sender import AlertSender
from ..research_data.calendar import SessionCalendar
from .comparison import changed
from .constants import (
    CONFIRM_LINE,
    CONFIRM_STARTS_UNTIL_SECONDS,
    CONFIRMED,
    DIFFERS_ALERT,
    FAILED_RUNS,
    INDICES,
    LEFT_FOR_NEXT_RUN,
    NO_FILE,
    NO_PREVIOUS_FILE,
    NOT_YET,
    NOT_YET_PREVIOUS,
    OVERDUE,
    OVERDUE_ALERT,
    OVERDUE_SESSIONS,
    RANGE_FIELDS,
    TOLERANCE,
)
from .official import OfficialCloses, OfficialValues
from .records import confirm_path, day_of, encode, overdue_path, record_path
from .store import ClosesStore

FAILED = "close confirm {day}: not confirmed ({kind}, message withheld); tried again next run"


class Confirmer:
    def __init__(self, store: ClosesStore, official: OfficialCloses, calendar: SessionCalendar, alerts: AlertSender,
                 log: Callable[[str], None] = print, now: Callable[[], datetime] | None = None):  # fmt: skip
        self.store, self.official, self.calendar, self.alerts, self.log = store, official, calendar, alerts, log
        self.now = now

    def run(self, today: date, started: datetime | None = None) -> None:
        """`started`: when the command began; no new day starts after the time budget (the rest wait a run). Newest
        first (judge 447 add. 2): an old day the archive keeps failing never takes the only slot from newer days."""
        written = self.store.written()
        pending = (d for d in map(day_of, written) if d is not None and d < today and confirm_path(d) not in written)
        days = sorted(pending, reverse=True)
        for done, day in enumerate(days):
            if started is not None and self._out_of_time(started):
                self.log(LEFT_FOR_NEXT_RUN.format(count=len(days) - done))
                return
            try:
                self._confirm(day, today, written)
            except Exception as error:  # noqa: BLE001 - one day's failure never stops the others or the read
                self.log(FAILED.format(day=day, kind=type(error).__name__))
                self._overdue_quietly(day, today, written)

    def _confirm(self, day: date, today: date, written: set[str]) -> None:
        found = self.official.values(day)
        provisional = json.loads(self.store.get(record_path(day)))["indices"] if found is not None else {}
        previous = self._previous(day, provisional) if found is not None else None
        if found is None or previous is None:
            line, why = (NOT_YET, NO_FILE) if found is None else (NOT_YET_PREVIOUS, NO_PREVIOUS_FILE)
            if not self._overdue(day, today, written, why):
                self.log(line.format(day=day))
            return
        filename, official = found
        lasts, fields = _compare(provisional, official, previous)
        self.store.put(confirm_path(day), encode({"day": day.isoformat(), "official_file": filename,
                                                  "confirmed_on": today.isoformat(), "indices": lasts,
                                                  "fields": fields}))  # fmt: skip
        text = ", ".join(f"{name} {last}{changed(fields[name], CONFIRMED)}" for name, last in lasts.items())
        self.log(CONFIRM_LINE.format(day=day, results=text))
        if not _all_confirmed(lasts, fields):
            announce(self.alerts, DIFFERS_ALERT.format(day=day, results=text))

    def _previous(self, day: date, provisional: dict) -> OfficialValues | None:
        """The previous session's official values when the record holds a previous close (A4h-2); {} when it holds
        none (a record from before A4h-2); None while that session's file is not there yet."""
        if not any(values.get("previous_close") is not None for values in provisional.values()):
            return {}
        found = self.official.values(self.calendar.previous_session(day))
        return found[1] if found is not None else None

    def _out_of_time(self, started: datetime) -> bool:
        return self.now is not None and (self.now() - started).total_seconds() >= CONFIRM_STARTS_UNTIL_SECONDS

    def _overdue(self, day: date, today: date, written: set[str], why: str) -> bool:
        """True from the second session after the day on; the first such run writes the mark and alerts once."""
        if len(self.calendar.sessions(day + timedelta(days=1), today)) < OVERDUE_SESSIONS:
            return False
        if overdue_path(day) not in written:
            self.store.put(overdue_path(day), encode({"day": day.isoformat(), "unconfirmed_on": today.isoformat()}))
            self.log(OVERDUE.format(day=day, today=today, why=why))
            announce(self.alerts, OVERDUE_ALERT.format(day=day, today=today, why=why))
        return True

    def _overdue_quietly(self, day: date, today: date, written: set[str]) -> None:
        try:
            self._overdue(day, today, written, FAILED_RUNS)
        except Exception as error:  # noqa: BLE001 - Drive down too: the next run tries the mark again
            self.log(FAILED.format(day=day, kind=type(error).__name__))


def _compare(provisional: dict, official: OfficialValues, previous: OfficialValues) -> tuple[dict, dict]:
    """`last`'s status per index (the shape A4h wrote), and each other field's (A4h-2)."""
    results = {n.listed: _results(provisional[n.listed], official.get(n.official), previous.get(n.official),
                                  n.checked) for n in INDICES}  # fmt: skip
    return {name: last for name, (last, _) in results.items()}, {name: rest for name, (_, rest) in results.items()}


def _all_confirmed(lasts: dict[str, str], fields: dict[str, dict[str, str]]) -> bool:
    """The checked indices only: INDIA VIX's differences are recorded, never alerted."""
    checked = [n.listed for n in INDICES if n.checked]
    return all(status == CONFIRMED for name in checked for status in (lasts[name], *fields[name].values()))


def _results(mine: dict, official: dict | None, previous: dict | None, checked: bool) -> tuple[str, dict[str, str]]:
    """`last`'s status, then each other recorded field's: the day range against the official file's, the previous
    close against the previous session's official close."""
    theirs = {"high": (official or {}).get("high"), "low": (official or {}).get("low"),
              "previous_close": (previous or {}).get("close")}  # fmt: skip
    fields = {key: _status(mine[key], theirs[key], checked) for key in RANGE_FIELDS if mine.get(key) is not None}
    return _status(mine["last"], (official or {}).get("close"), checked), fields


def _status(provisional: float, official: float | None, checked: bool) -> str:
    if official is None:
        return "not in the official file"
    gap = abs(provisional - official)
    if gap <= TOLERANCE + 1e-9:
        return CONFIRMED
    return f"differs by {gap:.2f}" + ("" if checked else " (list value)")
