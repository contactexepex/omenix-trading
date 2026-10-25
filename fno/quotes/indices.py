"""The other traded index options at 3 pm (story A4c; owner, 15 Oct 2026): BANKNIFTY, FINNIFTY and MIDCPNIFTY, recorded
right after NIFTY's push, inside 15:01-15:13 IST (after A16's 15:00 snapshot, before the 15:13 forecast cut-off and the
15:15 snapshots that share the Groww key), paced. One attempt per index in turn; an incomplete one is retried while the
window lasts (A4's rule), and an index still incomplete at its end is "none" for the day. Never places orders."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, time

from ..models import IST
from .recorder import (
    NOT_LISTED,
    RETRY_GAP_SECONDS,
    UNIVERSE,
    QuoteSnapshotRecorder,
    RecordResult,
    earliest_waiting_moment,
    earliest_waiting_start,
)
from .slot import Slot
from .weekly import NO_WEEKLY, WEEKLY_EXPIRIES

INDEX_WINDOW_START, INDEX_WINDOW_END = time(15, 1), time(15, 13)
INDEX_WORKERS, INDEX_PER_SECOND = 3, 2.5  # with A16's 5 a second, under the about 10 where Groww began failing
NOT_STARTED = RecordResult("window closed")
ATTEMPTED = "recorded"  # the status of every in-window attempt, complete or not; each one wrote its sidecar
QUIET_STATUSES = ("not a trading day", "already recorded")  # nothing to record and nothing to alert
DONE_WITHOUT_ATTEMPT = (*QUIET_STATUSES, "too early")  # never attempted, so never closed none
# The earliest start that still reaches the window by waiting (A4c-2: 15:01 minus the 20-minute early wait). A run
# started before it records nothing and writes no none marker, so its result says so (DRY2 R1, 24 Oct 2026).
EARLIEST_START = earliest_waiting_start(INDEX_WINDOW_START)
TOO_EARLY_REASON = (
    f"not started: too early (before {EARLIEST_START:%H:%M}); a rerun from {EARLIEST_START:%H:%M} to "
    f"{INDEX_WINDOW_END:%H:%M} records it"
)  # judge 568 minor 1: what to do
CLOSED_NONE = "canonical none"  # the day's marker was written "none": a rerun records nothing more


def index_slot(underlying: str, weeklies: int = 0) -> Slot:
    """A4c's slot; with `weeklies`, A4f's NIFTY weekly slot (stem `niftyweekly`), same window and pace."""
    return Slot(underlying, cross_check=False, stop_requests_at=INDEX_WINDOW_END, workers=INDEX_WORKERS,
                per_second=INDEX_PER_SECOND, check_listed=True, weeklies=weeklies,
                stem_suffix="weekly" if weeklies else "")  # fmt: skip


def weekly_slot() -> Slot:
    return index_slot("NIFTY", weeklies=WEEKLY_EXPIRIES)


class IndexRecording:
    def __init__(self, recorders: Mapping[str, QuoteSnapshotRecorder], now: Callable[[], datetime],
                 sleep: Callable[[float], None]):  # fmt: skip
        self.recorders, self.now, self.sleep = dict(recorders), now, sleep

    def run(self) -> dict[str, RecordResult]:
        now = self.now()
        day = now.date()
        if not next(iter(self.recorders.values())).is_session(day):
            return dict.fromkeys(self.recorders, RecordResult("not a trading day"))
        start, end = (datetime.combine(day, moment, IST) for moment in (INDEX_WINDOW_START, INDEX_WINDOW_END))
        if now < earliest_waiting_moment(day, INDEX_WINDOW_START):
            return dict.fromkeys(self.recorders, RecordResult("too early", reason=TOO_EARLY_REASON))
        if now < start:
            self.sleep((start - now).total_seconds())
        results = {name: self._done(recorder, day) or NOT_STARTED for name, recorder in self.recorders.items()}
        pending = [name for name, result in results.items() if result is NOT_STARTED]
        while pending and self.now() <= end:
            for underlying in list(pending):
                if self.now() > end:  # an index's expiry and chain calls never start after the window either
                    break
                results[underlying] = result = self.recorders[underlying].attempt_now()
                if result.complete or result.status != ATTEMPTED or _final(result.reason):
                    pending.remove(underlying)
            if pending:
                self.sleep(RETRY_GAP_SECONDS)
        for underlying, result in results.items():
            if closes_none(result):
                self.recorders[underlying].close_day(day)
        return results

    @staticmethod
    def _done(recorder: QuoteSnapshotRecorder, day) -> RecordResult | None:
        """A rerun on a day already recorded says so, inside the window or after it, like NIFTY's `record`."""
        marker = recorder.canonical(day)
        return RecordResult("already recorded", marker) if marker is not None else None


def closes_none(result: RecordResult) -> bool:
    """The day of an index not recorded is closed "none" at the window's end; never one not attempted for the day's
    reason (closed market, already recorded, too early). The one test for the close and for its "canonical none"."""
    return not result.complete and result.status not in DONE_WITHOUT_ATTEMPT


def _final(reason: str) -> bool:
    """A retry cannot help: the previous session's NSE file does not list the index, or cannot be read; or no NIFTY
    weekly is listed (A4f: the day ends "none" at once, so a rerun reads it as recorded)."""
    return reason in (NOT_LISTED, NO_WEEKLY) or reason.startswith(f"{UNIVERSE}:")
