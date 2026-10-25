"""A routine's own timing of its run (owner's "5 A" of 15 Oct 2026: the routine records its own usage at the end of
each run). A routine cannot read its own `result` event before its turn ends, and a fired routine runs one turn, so at
its end the session tools show none of that run's usage. What it can record is its own wall time: it notes the time when
it starts and when it ends, with its session id from `get_session` (no id: the calling session), in a JSON file
`{"session_id", "model", "started_at", "ended_at"}`. Tokens are unknown. The run is over when the file is written, so
its day is complete for this session.

Story BG1-w (owner, 24 Oct 2026: "Waiting minutes - Option A"): an AI book's file also holds `sealed_at` (G11). A run
that sealed counts its working minutes, start to seal; the wait from the seal to the end (the reveal) is kept apart in
`wait_minutes`, never capped. A run that never sealed (`sealed_at` null) follows `NO_SEAL_RULE`. A file without the
key (a data routine, the post-mortem, a book file from before G11) is read start to end, as before."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from . import constants
from .constants import NO_SEAL_RULES, NO_SEAL_UNKNOWN, NO_SEAL_UPPER_BOUND
from .usage_reader import DayUsage, ExportRefused, SessionUsageReader, ist_time, shaped

SOURCE = "self-timed by the routine (start to end of its run)"
SPLIT_SOURCE = "self-timed by the routine (start to seal; the wait to the end apart)"
UPPER_BOUND_SOURCE = f"self-timed by the routine ({NO_SEAL_UPPER_BOUND}: never sealed; start to end counted)"
SEALED_AT = "sealed_at"
MAX_RUN = timedelta(hours=24)  # longer is a typo, not a run: refused, never recorded
LATER_THAN_TODAY = "ended_at {day} is after today ({today}): a run cannot end in the future"
BACKWARDS = "ended_at {end} is before started_at {start}"
NEVER_SEALED = "working minutes unknown: the run never sealed (no_seal_unknown)"
SEAL_OUTSIDE = "sealed_at {seal} is not between started_at {start} and ended_at {end}"


class SelfTimedUsageReader(SessionUsageReader):
    def __init__(self, path: Path, no_seal: str | None = None):
        """`no_seal`: the rule for a run that never sealed; None takes the switch, `NO_SEAL_RULE`."""
        no_seal = constants.NO_SEAL_RULE if no_seal is None else no_seal
        if no_seal not in NO_SEAL_RULES:
            raise ValueError(f"the no-seal rule must be one of {NO_SEAL_RULES}, not {no_seal!r}")
        self._record = shaped(json.loads(path.read_text(encoding="utf-8")), dict, "the timing record")
        self._no_seal = no_seal

    def days(self) -> list[DayUsage]:
        start = ist_time(self._record.get("started_at") or "", "started_at")
        end = ist_time(self._record.get("ended_at") or "", "ended_at")
        if end < start:
            raise ExportRefused(BACKWARDS.format(end=end.isoformat(), start=start.isoformat()))
        if end - start > MAX_RUN:
            raise ExportRefused(f"the run lasted {end - start}, more than {MAX_RUN}: check started_at and ended_at")
        session_id = self._record.get("session_id") or ""
        if not session_id:
            raise ExportRefused("the timing record has no session_id")
        minutes, wait, source = self._split(start, end)
        # a run that crosses midnight IST counts on the day it ended
        model = self._record.get("model") or ""
        return [DayUsage(end.date(), session_id, model, minutes, 1, None, source, wait)]

    def complete_before(self, today: date) -> date:
        day = self.days()[0].day
        if day > today:
            raise ExportRefused(LATER_THAN_TODAY.format(day=day, today=today))
        return day + timedelta(days=1)

    def _split(self, start: datetime, end: datetime) -> tuple[float, float | None, str]:
        """(counted minutes, the wait kept apart, the source)."""
        if SEALED_AT not in self._record:
            return _minutes(start, end), None, SOURCE
        sealed = self._record[SEALED_AT]
        if sealed is None or sealed == "":
            if self._no_seal == NO_SEAL_UNKNOWN:
                raise ExportRefused(NEVER_SEALED)
            return _minutes(start, end), None, UPPER_BOUND_SOURCE
        seal = ist_time(sealed, SEALED_AT)
        if not start <= seal <= end:
            raise ExportRefused(
                SEAL_OUTSIDE.format(seal=seal.isoformat(), start=start.isoformat(), end=end.isoformat())
            )
        working = _minutes(start, seal)
        return working, round(_minutes(start, end) - working, 2), SPLIT_SOURCE  # the two parts add up to the run


def _minutes(start: datetime, end: datetime) -> float:
    return round((end - start).total_seconds() / 60, 2)
