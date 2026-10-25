"""One stress-factor run (story A14c): coverage first, then the largest needed factor, then one row in the factor file.

Full or incremental. The rule is a maximum over a window that only grows, so an incremental run reads the sessions
from `LOOKBACK_DAYS` before the last row's `coverage_through` (longer than any holding) and counts only the holdings
that end after it, taking the larger of their needed factor (`held_rise`) and the last `unrounded`. The first run,
and any run after a row with an empty `unrounded` (the owner's seed), is full, so a hand value never becomes a floor
(judge 176). Every file must be the archive's first copy (its SHA-256 equals the manifest's) and written before 09:00
IST on its day (A14's point-in-time rule). Files are read ahead by `workers` threads but fed in day order. Any
refusal (a download error included) writes nothing and sends one #fno-desk line; so does every row written."""

from __future__ import annotations

import hashlib
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from ..alerts.sender import AlertSender
from ..fo_bhavcopy import BadFile
from .held_rise import HeldRiseTracker, Holding
from .job import DayFile
from .prefetch import in_order
from .span_file import SpanFile, read_span_file
from .stress_coverage import FIRST_SESSION, CoverageGap, check_coverage, required_sessions
from .stress_evidence import build_evidence
from .stress_log import NextRow, StressFactorFile, StressRowRefused, decide

LOOKBACK_DAYS = 60  # a holding lasts at most about 44 calendar days (expiry 30-65 days out, exit 21 days before)
WRITTEN = "Omenix F&O stress factor {run_day}: {status} {factor:g} (computed {computed:g}, was {was:g}); peak {peak}"
HELD_ASK = "; a lower value waits for the owner: approve it with a DESK_DECISIONS row, then rerun with --approve-fall"
DROPPED = "; {count} holding(s) dropped or not entered (named in the evidence)"
REFUSED = "Omenix F&O stress factor {run_day}: nothing written: {reason}"


@dataclass(frozen=True)
class StressSources:
    day_file: DayFile  # a session's first-archived i1 file; called from `workers` threads at once
    archived: Callable[[], Mapping[date, str]]  # the manifest: session -> SHA-256
    is_trading_day: Callable[[date], bool]
    new_tracker: Callable[[], HeldRiseTracker]
    first_session: date = FIRST_SESSION
    workers: int = 1  # downloads running ahead of the day being read (prefetch.in_order)


class StressFactorRun:
    def __init__(self, sources: StressSources, factor_file: StressFactorFile, evidence_folder: Path,
                 alerts: AlertSender, run_day: date, print_line=print):  # fmt: skip
        self.sources, self.factor_file, self.evidence_folder = sources, factor_file, evidence_folder
        self.alerts, self.run_day, self.print_line = alerts, run_day, print_line

    def run(self, full: bool = False, approved_fall: str | None = None) -> int:
        try:
            line = self._run(full, approved_fall)
        except (CoverageGap, StressRowRefused, BadFile) as exc:
            return self._refused(exc)
        except Exception as exc:  # e.g. Drive consent expired, a calendar year missing: still one line, never silent
            traceback.print_exc()
            return self._refused(f"stopped by an unexpected {type(exc).__name__}: {exc}")
        self.print_line(self.alerts.send(line))
        return 0

    def _refused(self, reason) -> int:
        self.print_line(self.alerts.send(REFUSED.format(run_day=self.run_day, reason=reason)))
        return 1

    def _run(self, full: bool, approved_fall: str | None) -> str:
        required = required_sessions(self.run_day, self.sources.is_trading_day, self.sources.first_session)
        coverage = check_coverage(required, self.sources.archived())
        last = self.factor_file.last()
        full = full or last.unrounded is None or last.coverage_through is None
        start = self.sources.first_session if full else last.coverage_through - timedelta(days=LOOKBACK_DAYS)
        tracker = self._read([d for d in required if d >= start], coverage.files)
        counted = [h for h in tracker.found.completed if full or h.exit > last.coverage_through]
        carried = None if full else last.unrounded
        if not counted and carried is None:
            raise StressRowRefused("no holding completed in the archive")
        new_max = max((h.needed for h in counted), default=0.0)
        unrounded = max(new_max, carried or 0.0)
        factor, computed, status = decide(last, unrounded, approved_fall)
        fell = approved_fall if factor < last.factor else None  # the approval is named only on a real fall
        peak = _peak(counted, new_max, carried, last.coverage_through, fell)
        evidence = build_evidence(self.run_day, counted, coverage.files, unrounded, (factor, computed, status),
                                  tracker.found.dropped, "full" if full else "incremental")  # fmt: skip
        evidence.write(self.evidence_folder, self.run_day)
        self.factor_file.append(NextRow(self.run_day, factor, computed, unrounded, status, peak, coverage.through,
                                        evidence.sha256))  # fmt: skip
        line = WRITTEN.format(run_day=self.run_day, status=status, factor=factor, computed=computed, was=last.factor,
                              peak=peak)  # fmt: skip
        dropped = len(tracker.found.dropped)
        return line + (DROPPED.format(count=dropped) if dropped else "") + (HELD_ASK if status == "held" else "")

    def _read(self, days: list[date], sha256: Mapping[date, str]) -> HeldRiseTracker:
        tracker = self.sources.new_tracker()
        try:
            for day, (filename, data) in in_order(self.sources.day_file, days, self.sources.workers):
                tracker.feed(day, self._span(filename, data, day, sha256[day]))
        except OSError as exc:  # Drive unreachable or refusing (requests' errors are OSErrors): nothing is written
            raise StressRowRefused(f"the archive could not be read: {exc}") from exc
        return tracker

    def _span(self, filename: str, data: bytes | None, day: date, sha256: str) -> SpanFile:
        if data is None:
            raise StressRowRefused(f"{filename} is in the manifest but not in the archive")
        if hashlib.sha256(data).hexdigest() != sha256:
            raise StressRowRefused(f"{filename} differs from its manifest SHA-256 (not the first-archived copy)")
        span = read_span_file(data, filename, allow_short_option_minimum=True)
        if not span.written_in_time(day):
            raise StressRowRefused(f"{filename} was written {span.created:%Y-%m-%d %H:%M}, not before 09:00 on its day")
        return span


def _peak(counted: list[Holding], new_max: float, carried: float | None, through: date | None,
          approved: str | None) -> str:  # fmt: skip
    if carried is not None and carried >= new_max:
        text = f"carried from the run through {through}"
    else:
        h = max(counted, key=lambda h: (h.needed, -h.entry.toordinal()))
        text = f"{h.structure} {h.width:g} entered {h.entry} peak {h.peak_day} needed {h.needed:.4f}"
    return text + (f"; fall approved by the owner, DESK_DECISIONS {approved}" if approved else "")
