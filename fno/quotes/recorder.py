"""Records real bid/ask quotes of NIFTY monthly options near the money at about 3 pm IST (story A4).

Only time builds this history: daily NSE files have no bid or ask. Each run is an immutable *attempt* saved under its
capture time; an incomplete attempt may be retried inside the window, and the day's canonical snapshot is the first
complete attempt (or "none"). Quotes are not fills. Never places, modifies or cancels orders.

Whether today is a session comes from NSE's session calendar (story A7), never from the weekday or from the quotes: a
special weekend session is recorded, a weekday holiday is not, and a session day with no same-day trade is a failure
to report (calendar says session, quotes say closed), not a quiet "not a trading day".
"""

from __future__ import annotations

import hashlib
import json
import time as clock
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from ..constants import SESSION_MUHURAT, SESSION_REGULAR, SESSION_SPECIAL
from ..intraday.pacing import RatePacer
from ..models import IST, OptionChain, now_ist
from ..providers.base import Provider
from ..research_data.calendar import SessionCalendar
from ..research_data.expiries import MONTHLY_LISTING_DAYS
from ..research_data.expiries import monthly_expiries as last_expiry_of_each_month
from ..storage.raw_store import RawFileStore
from .book_fetch import BookFetcher
from .capture_extras import CaptureExtras
from .capture_log import CaptureLog
from .expiry_listing import ExpiryHistory, ListedExpiries
from .market_levels import LevelSource
from .monthly_contracts import PointInTimeMonthlies
from .quote_validity import quote_validity, traded_today  # noqa: F401 - quote_validity imported from here by E8
from .slot import NIFTY_SLOT, Slot
from .snapshot_rows import (
    COLUMNS,  # noqa: F401 - imported from here by the frozen tools/forecast_live_golden.py
    snapshot_csv,
    snapshot_row,
)
from .weekly import NO_WEEKLY, nearest_weeklies
from .window import QuoteWindow

DATASET = "groww/derivatives/quote-snapshots"
NSE_DATASET = "nse/derivatives/quote-snapshots"  # story O6: NSE's public chain, never mixed with Groww's
WINDOW_START, WINDOW_END = time(14, 55), time(15, 10)
MAX_EARLY_WAIT_SECONDS = 20 * 60  # a run started up to 20 minutes early waits for the window
DEFAULT_WINDOW = QuoteWindow("", WINDOW_START, WINDOW_END, MAX_EARLY_WAIT_SECONDS)  # A4's, never changed


def earliest_waiting_moment(day: date, window_start: time, max_early_wait: int = MAX_EARLY_WAIT_SECONDS) -> datetime:
    """A4's early limit, its one rule (A4c-2): a run started before this moment of `day` says "too early" and records
    nothing; from it on, the run waits for the window opening at `window_start`. On the real day, so a named window's
    longer wait (A4e's config) never crosses `date.min`."""
    return datetime.combine(day, window_start, IST) - timedelta(seconds=max_early_wait)


def earliest_waiting_start(window_start: time) -> time:
    """That moment as a time of day, with A4's 20 minutes: 14:41 for 15:01, 14:35 for 14:55 (for texts and O1's start
    times); O1's `fno/daily/quote_parts.py` `earliest_start` builds on it. A window opening before 00:20 has no such
    time of day (OverflowError); no window does."""
    return earliest_waiting_moment(date.min, window_start).time()


RETRY_GAP_SECONDS = 60
SPOT_BAND = 0.05  # strikes within 5% of spot
MONTHLY_EXPIRIES = 2
WEEKEND_START = 5  # only when built without a calendar (the A4 tests): weekends closed, no same-day trade = holiday
RECORDED_SESSION_KINDS = (SESSION_REGULAR, SESSION_SPECIAL)  # a muhurat session is one evening hour, not 14:55-15:10
MUHURAT_ONLY = "muhurat session only: the market is closed from 14:55 to 15:10"
NO_SAME_DAY_TRADES = "calendar says session, no same-day trades"
NOT_LISTED = "not listed as an index option in the previous session's NSE file"
UNIVERSE = "universe"  # where a failure to read the previous session's NSE file is reported (A4c)
VERIFIED, UNVERIFIED = "verified", "unverified"  # status of meta.json's monthly_check
POINT_IN_TIME_RULE = f"listed more than {MONTHLY_LISTING_DAYS} days ahead by that day (A5 monthly_as_of)"
FALLBACK_RULE = "last listed expiry of month"
NONE_MARKER = "none"
RAW_FILE_NOT_SAVED = "raw quote file not saved"
MESSAGE_WITHHELD = "provider message withheld"
RAW_FILE_SAVED = "raw_file_saved"  # sidecar key, written (false) only when the save failed: absent means saved (A4b)


def monthly_expiries(expiries: list[date], today: date, count: int = MONTHLY_EXPIRIES) -> list[date]:
    """The nearest `count` monthly contracts: the last listed expiry of each calendar month, from today on. Used only
    by a recorder built without NSE's expiry history (the A4 tests); the app uses `PointInTimeMonthlies` (A5's rule)."""
    return sorted(last_expiry_of_each_month({e for e in expiries if e >= today}))[:count]


GROWW_NOTE = "quotes, not fills; Groww gives no quote timestamp: quote age unknown, valid needs a trade today"
NSE_NOTE = "quotes, not fills; NSE public option chain: quote_time is its page timestamp, traded today = day volume > 0"
PROVIDER_NOTES = {"nse": NSE_NOTE}


class _NotRecorded(Exception):
    """The attempt asks the provider nothing (its underlying is not listed); the reason is already in `failures`."""


@dataclass
class RecordResult:
    status: str  # recorded, already recorded, not a trading day, window closed, too early
    snapshot_id: str = ""
    complete: bool = False
    rows: int = 0
    reason: str = ""  # why a session day was skipped or failed the calendar cross-check
    monthly_unverified: str = ""  # why the monthly contracts were chosen by the fallback rule (alerted, never hidden)
    raw_file_error: str = ""  # why the quote file was not saved (A4b: Drive only; alerted, never saved elsewhere)
    raw_file_detail: str = ""  # the error's own text: for the private alert only, never in a committed file


class QuoteSnapshotRecorder:
    def __init__(self, provider: Provider, store: RawFileStore, clock_now=now_ist, sleep=clock.sleep,
                 fallback: ListedExpiries | None = None, calendar: SessionCalendar | None = None,
                 history: ExpiryHistory | None = None, levels: LevelSource | None = None,
                 dataset: str = DATASET, slot: Slot = NIFTY_SLOT, window: QuoteWindow = DEFAULT_WINDOW,
                 log: CaptureLog | None = None, extras: CaptureExtras | None = None):  # fmt: skip
        """The app always passes `calendar` and `history` (fno/composition.py). Without them (the A4 tests and
        byte-identical baseline), A4's rules stay: weekends are closed, a day with no same-day trade is a holiday, and
        the monthly is the last listed expiry of each month."""
        self.provider, self.store, self.now, self.sleep = provider, store, clock_now, sleep
        self.fallback, self.calendar, self.levels, self.dataset = fallback, calendar, levels, dataset
        self.monthly_check = PointInTimeMonthlies(history) if history else None
        self.slot, self.underlying, self.window, self.log = slot, slot.underlying, window, log  # log: A4e only
        self.extras = extras  # G10: the `v4` window's V4 expiry and future quote, never counted for completeness
        self.pacer = RatePacer(slot.per_second) if slot.per_second else None  # one per recorder, across attempts

    @staticmethod
    def path(day: date, name: str, dataset: str = DATASET) -> str:
        return f"{dataset}/{day:%Y}/{day:%m}/{name}"

    def _path(self, day: date, name: str) -> str:
        return self.path(day, name, self.dataset)

    def canonical(self, day: date) -> str | None:
        data = self.store.get(self._marker(day))
        return data.decode().strip() if data else None

    def _marker(self, day: date) -> str:
        return self._path(day, f"{self.slot.stem}_{day:%Y%m%d}.canonical")

    def record(self, outside_window: bool = False) -> RecordResult:
        """One day's recording: waits for the window if early, retries incomplete attempts until the window ends.
        `outside_window` (testing only) makes one attempt now; such an attempt is never canonical.
        Raises `CalendarError` for a day outside the calendar's years (never guesses)."""
        now = self.now()
        day = now.date()
        kind = self._session_kind(day)
        if kind not in RECORDED_SESSION_KINDS:
            return RecordResult("not a trading day", reason=MUHURAT_ONLY if kind == SESSION_MUHURAT else "")
        if self.canonical(day) is not None:
            return RecordResult("already recorded", self.canonical(day))
        if outside_window:
            return self._attempt(day, canonical_allowed=False)
        start, end = (datetime.combine(day, t, IST) for t in (self.window.start, self.window.end))
        if now < earliest_waiting_moment(day, self.window.start, self.window.max_early_wait_seconds):
            return RecordResult("too early")
        if now < start:
            self.sleep((start - now).total_seconds())
        result = RecordResult("window closed")
        while self.now() <= end:
            result = self._attempt(day, canonical_allowed=True)
            if result.complete or result.status == "not a trading day":
                return result
            self.sleep(RETRY_GAP_SECONDS)
        self.close_day(day)
        return result

    def is_session(self, day: date) -> bool:
        return self._session_kind(day) in RECORDED_SESSION_KINDS

    def attempt_now(self) -> RecordResult:
        """One in-window attempt now, canonical if complete (story A4c: the index slots' runner keeps the window)."""
        day = self.now().date()
        if not self.is_session(day):
            return RecordResult("not a trading day")
        if self.canonical(day) is not None:
            return RecordResult("already recorded", self.canonical(day))
        return self._attempt(day, canonical_allowed=True)

    def close_day(self, day: date) -> None:
        """The window has ended: a day without a complete attempt is "none", never back-filled."""
        if self.canonical(day) is None:
            self.store.put(self._marker(day), NONE_MARKER.encode())

    def capture(self) -> RecordResult:
        """One more capture now, never canonical, by A4's own rules (story E3's execution snapshot at about 15:15).
        Records nothing on a day that is not a recorded session."""
        day = self.now().date()
        if self._session_kind(day) not in RECORDED_SESSION_KINDS:
            return RecordResult("not a trading day")
        return self._attempt(day, canonical_allowed=False)

    def _session_kind(self, day: date) -> str | None:
        """The calendar's answer; without a calendar (A4 tests), every weekday is a regular session."""
        if self.calendar is None:
            return SESSION_REGULAR if day.weekday() < WEEKEND_START else None
        return self.calendar.session_kind(day)

    def _nearest_monthlies(self, listed: list[date], day: date, check: dict) -> list[date]:
        """The nearest monthly contracts by A5's point-in-time rule, with the NSE files that proved them in `check`.
        If that history cannot be read, the last-of-month rule is used and `check` says so: a lost day of quotes can
        never be recorded later, while a flagged contract choice can be verified later. Without a history (the A4
        tests), the last-of-month rule is A4's own and nothing is flagged."""
        if self.monthly_check is None:
            return monthly_expiries(listed, day)
        try:
            monthly, used = self.monthly_check.monthlies(self.underlying, listed, day)
        except Exception as exc:
            check.update(status=UNVERIFIED, rule=FALLBACK_RULE, reason=withheld("expiry history", exc))
            return monthly_expiries(listed, day)
        if check.get("status") != UNVERIFIED:
            check.update(status=VERIFIED, rule=POINT_IN_TIME_RULE)
            files = check.setdefault("files", [])
            files += [source for source in used if source not in files]
        return sorted(monthly)[:MONTHLY_EXPIRIES]

    def _attempt(self, day: date, canonical_allowed: bool) -> RecordResult:
        started = self.now()
        if self.log:
            self.log.begin()
        snapshot_id = f"{self.slot.stem}_{started:%Y%m%d_%H%M%S}"
        failures, rows, chains, expiry_source, check, found = [], [], [], {"source": self.provider.name}, {}, ([], [])
        universe = self._universe(day, failures) if self.slot.check_listed else None
        try:
            if failures:
                raise _NotRecorded
            listed = self.provider.expiries(self.underlying)
            months = self._nearest_monthlies(listed, day, check)
            if len(months) < MONTHLY_EXPIRIES and self.fallback:  # late December: Groww lists no next-year dates
                try:
                    listed, expiry_source = self.fallback.listed(self.underlying, day)
                    months = self._nearest_monthlies(listed, day, check)
                except Exception as exc:
                    failures.append(withheld("expiry fallback", exc))
            found = (listed, months)  # for the extras, asked only after every required field (judge 584 SF2)
            for expiry in self._targets(listed, months, day, failures):
                chains.append(self.provider.chain(self.underlying, expiry))
        except _NotRecorded:
            pass
        except Exception as exc:  # recorded, never hidden: the attempt is incomplete
            failures.append(withheld("chain", exc))
        levels = self.levels.levels(self.underlying) if self.levels else None  # inside the capture: before finished_at
        expected, traded = sum(len(self._contracts(c)) for c in chains), False
        for chain in chains:
            for got in self._fetcher(day).fetch(chain, self._contracts(chain)):
                if got.error is not None:
                    failures.append(withheld(f"{chain.expiry} {got.strike:g} {got.kind}", got.error))
                    continue
                rows.append(snapshot_row(snapshot_id, self.provider.name, got, chain, day))
                traded = traded or traded_today(got.book, day)
        asked = bool(self.extras and chains)  # G10's optional extras: last, and only on an attempt that got a chain
        extra = self.extras.capture(snapshot_id, day, *found) if asked else []
        if rows and not traded and self.slot.cross_check:
            if self.calendar is None:
                return RecordResult("not a trading day", snapshot_id)  # A4 inference: no contract traded, closed
            failures.append(NO_SAME_DAY_TRADES)  # kept and retried; the day ends "none" if it persists to 15:10
        csv_bytes = snapshot_csv([*rows, *extra])
        raw_file_error, raw_file_detail = self._save_quote_file(self._path(day, f"{snapshot_id}.csv"), csv_bytes)
        if raw_file_error:
            failures.append(raw_file_error)
        complete = bool(chains) and not failures and len(rows) == expected
        meta = {
            "snapshot_id": snapshot_id, "underlying": self.underlying, "provider": self.provider.name,
            "started_at": started.isoformat(), "finished_at": self.now().isoformat(),
            "expiries": [c.expiry.isoformat() for c in chains], "spot": chains[0].spot if chains else None,
            "expiry_source": expiry_source,
            "expected_contracts": expected, "recorded_contracts": len(rows), "failures": failures,
            "complete": complete, "in_window": canonical_allowed, "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
            "note": PROVIDER_NOTES.get(self.provider.name, GROWW_NOTE),
        }  # fmt: skip
        if raw_file_error:
            meta[RAW_FILE_SAVED] = False
        if self.log:
            meta.update(self.log.finish())  # A4e: each field's own times and the clock check
        meta.update(self.extras.meta() if asked else {})  # never an earlier attempt's
        if universe is not None:
            meta["universe"] = universe  # the NSE file that listed (or did not list) the underlying
        if self.monthly_check is not None:
            meta["monthly_check"] = check  # verified with the NSE files that proved it, or unverified and why
        if levels is not None:
            meta.update(levels.meta(), levels_source=self.levels.name)  # India VIX and futures for live features
        self.store.put(self._path(day, f"{snapshot_id}.meta.json"), json.dumps(meta, indent=1, sort_keys=True).encode())
        if complete and canonical_allowed and self.canonical(day) is None:
            self.store.put(self._marker(day), snapshot_id.encode())
        final = (NO_SAME_DAY_TRADES, NOT_LISTED, NO_WEEKLY)
        reason = next((f for f in failures if f in final or f.startswith(f"{UNIVERSE}:")), "")
        unverified = check["reason"] if check.get("status") == UNVERIFIED else ""
        return RecordResult("recorded", snapshot_id, complete, len(rows), reason, unverified, raw_file_error,
                            raw_file_detail)  # fmt: skip

    def _targets(self, listed: list[date], months: list[date], day: date, failures: list[str]) -> list[date]:
        """The expiries this slot records: A4's two monthlies, or the nearest weeklies around them (A4f). A weekly slot
        short of two monthlies records nothing: a weekly beside an unknown monthly is never taken."""
        if len(months) < MONTHLY_EXPIRIES:
            failures.append(f"only {len(months)} monthly expiries found")
            if self.slot.weeklies:
                return []
        if not self.slot.weeklies:
            return months
        weeklies = nearest_weeklies(listed, months, day, self.slot.weeklies)
        if not weeklies:
            failures.append(NO_WEEKLY)
        return weeklies

    def _universe(self, day: date, failures: list[str]) -> dict:
        """The previous session's NSE file (name, date, SHA-256) and whether it lists the underlying as an index
        option (story A4c: point in time, read once a run); a name it no longer lists is a failure, never skipped."""
        try:
            listed, provenance = self.fallback.listed(self.underlying, day)
        except Exception as exc:
            failures.append(withheld(UNIVERSE, exc))
            return {}
        if not listed:
            failures.append(NOT_LISTED)
        return provenance

    def _fetcher(self, day: date) -> BookFetcher:
        stop = self.slot.stop_requests_at
        stop_at = datetime.combine(day, stop, IST) if stop else None
        return BookFetcher(self.provider, self.now, self.slot.workers, self.pacer, stop_at)

    def _save_quote_file(self, path: str, data: bytes) -> tuple[str, str]:
        """("", "") when saved; otherwise (the reason for the public sidecar, the error's own text). The quote rows are
        then kept nowhere (A4b: never in the repository instead), and the attempt is incomplete, so it is never
        canonical and the window retries. The sidecar gets the error's type only: a Drive error's text can hold the
        request URL with the private folder's ID."""
        try:
            self.store.put(path, data)
        except Exception as exc:
            return f"{RAW_FILE_NOT_SAVED}: {type(exc).__name__}", str(exc)
        return "", ""

    @staticmethod
    def _contracts(chain: OptionChain) -> list[tuple[float, str]]:
        low, high = chain.spot * (1 - SPOT_BAND), chain.spot * (1 + SPOT_BAND)
        return sorted((k, t) for k, t in chain.quotes if low <= k <= high)


def withheld(where: str, exc: Exception) -> str:
    """A public sidecar's failure entry (A4b): the exception's type only. Its message can carry a request URL, a private
    Drive folder ID or a quoted value, and the sidecar is committed to the public repository."""
    return f"{where}: {type(exc).__name__} ({MESSAGE_WITHHELD})"
