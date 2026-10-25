"""The Asian index levels before NSE's 09:15 open (story A17e part B): one Yahoo 5-minute read per Asian index that is
open by about 08:50 IST, called from A22's pre-open routine between its GIFT Nifty and pre-open windows.

Each read archives the raw answer in Drive with its snapshot-log row (A17's write-once rule) before parsing it (A17f:
an empty or broken answer keeps its bytes), then appends one row to the private table in Drive: the index, when we saw
it, the time and value of its newest 5-minute level, that index's previous close (A17e's reading at the open, live
view: what was known then), a status and its reason:
- `live`: the newest level is at most `STALE_AFTER` old when seen;
- `stale`: older than that (Yahoo's feed paused or delayed);
- `market closed`: the market's closures calendar lists today (A17f; no request is sent), or, for a market without a
  calendar, the newest level is not from today in the market's own time zone (inferred from Yahoo, not proven);
- `no session data` (A17f): Yahoo's chart with no level in it, or, for a market with a calendar, only an earlier day's
  levels on a day the calendar does not list: closed unannounced (a typhoon) or a Yahoo gap, not told apart at 08:50.
A block (HTTP 401, 403 or 429, a redirect, a page that is not chart data) stops that index with no retry, exactly as
A17e's daily Yahoo cues (owner rule 50a79a43, rule 2); the other indexes still run.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from ..models import IST
from ..storage.row_log import RowLog
from .markets import MarketClose
from .preopen_calendar import CalendarVerdict, ClosureCalendar
from .preopen_outcome import INCOMPLETE, Problem, ReadOutcome
from .snapshot_log import SnapshotLog, SnapshotRow
from .source import CueRequest, positive
from .yahoo_source import YahooChartSource

YAHOO_INTRADAY = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=5m"
STALE_AFTER = timedelta(minutes=20)
LIVE, STALE, CLOSED, LUNCH = "live", "stale", "market closed", "lunch break"
NO_DATA, FAILED = "no session data", "failed"
BAR = timedelta(minutes=5)
ROW_FIELDS = (
    "index", "seen_at", "level_time", "level", "status", "previous_close", "previous_close_cue", "sha256", "reason",
    "settles",
)  # fmt: skip
RAW_FOLDER = "yahoo/preopen"
EMPTY, EARLIER = "empty answer", "newest level from an earlier day"
UNTOLD = "closed unannounced or a Yahoo gap"
NOT_SETTLED = "; no official table, not settled"
SHA_SHOWN = 12


class EmptyAnswer(Exception):
    """Yahoo's chart answer with no level in it: no session data, not a failure (A17f rule 2)."""


@dataclass(frozen=True)
class PreopenLevel:
    index: str
    seen_at: datetime
    level_time: datetime
    level: float  # private: never printed
    status: str


def level_status(seen_at: datetime, level_time: datetime, market: MarketClose) -> str:
    """`market closed` (no level today), `lunch break` (the market's midday break: the morning's last level), else
    `live` or `stale` by the level's age."""
    zone = ZoneInfo(market.zone)
    if level_time.astimezone(zone).date() != seen_at.astimezone(zone).date():
        return CLOSED
    if market.at_lunch(seen_at):
        return LUNCH
    return STALE if seen_at - level_time > STALE_AFTER else LIVE


def newest_level(index: str, data: bytes, seen_at: datetime, market: MarketClose) -> PreopenLevel:
    """The newest 5-minute close in a Yahoo chart answer, timed at its bar's end (or now, for the bar still running).
    EmptyAnswer for Yahoo's chart with no timestamp, an empty quote object or no non-null close; ValueError for any
    other layout. Never shows a level in an error."""
    zone, stamps, closes = _chart(data, index)
    if all(c is None for c in closes) and (not stamps or len(stamps) == len(closes)):
        raise EmptyAnswer(index)
    if len(stamps) != len(closes):
        raise ValueError(f"{index}: not one close per timestamp in Yahoo's answer")
    stamp, level = [(t, c) for t, c in zip(stamps, closes, strict=True) if c is not None][-1]
    try:
        bar_start = datetime.fromtimestamp(stamp, ZoneInfo(zone))
    except (OverflowError, OSError, TypeError):
        raise ValueError(f"{index}: an impossible timestamp in Yahoo's answer") from None
    level_time = min(bar_start + BAR, seen_at)
    value = positive(level, index, True)
    return PreopenLevel(index, seen_at, level_time, value, level_status(seen_at, level_time, market))


def _chart(data: bytes, index: str) -> tuple[str, list, list]:
    """The answer's time zone, timestamps and closes. An empty quote object (or none) gives no closes; ValueError
    unless it is Yahoo's chart (result, meta's time zone, a quote list) whose timestamps and closes, when given, are
    lists: a quote object without a `close` list is a changed layout, not an empty answer."""
    try:
        result = json.loads(data)["chart"]["result"][0]
        zone, quotes = result["meta"]["exchangeTimezoneName"], result["indicators"]["quote"]
        quote = quotes[0] if quotes else {}
        closes = quote["close"] if quote else []
        stamps = result.get("timestamp") or []
        if not all(isinstance(part, list) for part in (quotes, closes, stamps)) or not isinstance(zone, str):
            raise TypeError("not a list")
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ValueError(f"{index}: not Yahoo's chart answer ({type(exc).__name__})") from None
    return zone, stamps, closes


class PreopenReader:
    def __init__(
        self,
        session: requests.Session,
        archive,
        log: SnapshotLog,
        rows: RowLog,
        previous_close: Callable[[str, datetime], tuple[str, str]],
        clock: Callable[[], datetime],
        calendars: dict[str, ClosureCalendar] | None = None,
        settled: frozenset[str] = frozenset(),
    ):
        """`previous_close(index, seen_at)`: the index's value and cue known at the open ("" when none); `calendars`:
        the indexes whose market has a closures calendar; `settled`: those with an official daily table, whose
        `no session data` is settled later (A17f rule 3)."""
        self.session, self.archive, self.log, self.rows = session, archive, log, rows
        self.previous_close, self.clock = previous_close, clock
        self.calendars, self.settled = calendars or {}, settled

    def read(self, source: YahooChartSource, index: str) -> ReadOutcome:
        """One index's outcome; raises requests.RequestException (a block included) or ValueError (Drive, a level)."""
        calendar = self.calendars.get(index)
        verdict = CalendarVerdict(None)
        if calendar:
            verdict = calendar.verdict(index, self.clock().astimezone(ZoneInfo(source.market.zone)).date())
        if verdict.closure:
            self._append(index, self.clock().astimezone(IST), ("", ""), CLOSED, "", f"calendar: {verdict.closure.kind}")
            return ReadOutcome((*verdict.lines, verdict.closed_line(index, calendar.label)), CLOSED, verdict.problems)
        found = self._read_yahoo(source, index, calendar is not None)
        return ReadOutcome(verdict.lines + found.lines, found.status, verdict.problems + found.problems)

    def _read_yahoo(self, source: YahooChartSource, index: str, has_calendar: bool) -> ReadOutcome:
        request = CueRequest(f"{index}_5m.json", YAHOO_INTRADAY.format(symbol=source.symbol.replace("^", "%5E")))
        data = source.download(self.session, request)  # A17e's block rule: no retry, no other way
        seen_at = self.clock().astimezone(IST)
        sha256 = self._archive(index, request, data, seen_at)  # before parsing (A17f rule 5)
        try:
            level = newest_level(index, data, seen_at, source.market)
        except EmptyAnswer:
            return self._no_session_data(index, seen_at, sha256, EMPTY, ("", ""))
        except ValueError as exc:
            self._append(index, seen_at, ("", ""), FAILED, sha256, "changed layout (ValueError)")
            text = f"{index}: failed (ValueError: changed layout; raw {sha256[:SHA_SHOWN]})"
            return ReadOutcome(
                (f"{index}: FAILED (ValueError): {exc}; raw {sha256[:SHA_SHOWN]}",), FAILED, (Problem(text),)
            )
        stored = (level.level_time.isoformat(), repr(level.level))
        if level.status == CLOSED and has_calendar:
            return self._no_session_data(index, seen_at, sha256, EARLIER, stored)
        self._append(index, seen_at, stored, level.status, sha256, "")
        age = round((seen_at - level.level_time).total_seconds() / 60)
        line = f"{index}: {level.status}, level of {level.level_time:%H:%M} {level.level_time.tzname()} ({age} min old)"
        return ReadOutcome((line,), level.status)

    def _no_session_data(self, index: str, seen_at: datetime, sha256: str, why: str, stored: tuple) -> ReadOutcome:
        self._append(index, seen_at, stored, NO_DATA, sha256, f"{why}: {UNTOLD}")
        raw, final = f"raw {sha256[:SHA_SHOWN]}", "" if index in self.settled else NOT_SETTLED
        line = f"{index}: {NO_DATA} ({why}: {UNTOLD}; {raw}{final})"
        return ReadOutcome((line,), NO_DATA, (Problem(f"{index}: {NO_DATA} ({why}; {raw})", INCOMPLETE),))

    def _append(self, index: str, seen_at: datetime, stored: tuple, status: str, sha256: str, reason: str) -> None:
        close, close_cue = self.previous_close(index, seen_at)
        seen = seen_at.isoformat(timespec="seconds")
        self.rows.append(ROW_FIELDS, [(index, seen, *stored, status, close, close_cue, sha256, reason, "")])

    def _archive(self, index: str, request: CueRequest, data: bytes, seen_at: datetime) -> str:
        path = f"{RAW_FOLDER}/{seen_at:%Y/%m/%d}/{seen_at:%H%M%S}_{request.name}"
        sha256 = hashlib.sha256(data).hexdigest()
        self.archive.put(path, data)
        self.log.append(f"{index}_preopen", SnapshotRow(seen_at, path, request.url, (), sha256, len(data)))
        return sha256
