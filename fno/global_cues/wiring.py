"""Composition root of story A17, the global cues: the only place that picks the concrete sources (Cboe, Nasdaq, US
Treasury, EIA, RBI, FBIL), the shared polite HTTP session, the owner's Drive raw area, the snapshot logs, the tables in
the repository (public cues) or Drive's derived area (private cues: the S&P 500 and Nasdaq 100, owner decision a927390;
FBIL's USD/INR rate, story A17d), NSE's session calendar for the `live` rule, and each cue's calendar for its readings
(story A17b); story A17e's world indexes (official files where they answer without a login, Yahoo for the rest and
the history, one reading per index, every value private). Swapping a source is one line in SOURCES."""

from __future__ import annotations

import csv
import os
from collections.abc import Callable
from datetime import date, datetime

from ..circulars.episodes import OpenProblems
from ..constants import DERIVED_AREA, RESEARCH_USER_AGENT
from ..http_pacing import PacedSession
from ..models import now_ist
from ..research_data.calendar import SessionCalendar
from ..storage import wiring as storage
from ..storage.creation_times import GoogleDriveCreationTimes
from ..storage.owned_paths_commit import OwnedPathsCommitter
from ..storage.raw_store import AreaStore, RawFileStore
from ..storage.row_log import CsvRowLog, DrivePartsRowLog, DriveSnapshots
from .as_of import OPEN
from .asia_sources import CsindexShanghaiSource, NikkeiSource, TwseTaiexSource
from .behind import BehindCheck
from .check_files import CueChecks
from .collector import CueCollector
from .cue_calendars import CueCalendar, NseSessionCalendar, NyseCalendar, WeekdayCalendar
from .europe_sources import CboeVixSource, StoxxSource
from .index_reader import IndexPair, IndexReader
from .job import GlobalCueJob
from .market_closures import load_closures
from .markets import (
    CBOE_VIX,
    EURO_STOXX,
    FRANKFURT,
    HONG_KONG,
    LONDON,
    NEW_YORK,
    SEOUL,
    SHANGHAI,
    SINGAPORE,
    SYDNEY,
    TAIPEI,
    TOKYO,
)
from .other_sources import EiaBrentSource, FbilUsdInrSource, RbiUsdInrSource
from .preopen import PreopenReader
from .preopen_calendar import ClosureCalendar
from .reading import CueReader, CueReading
from .snapshot_log import SnapshotLog
from .source import GlobalCueSource
from .table import CueTable
from .treasury_source import TreasuryTenYearSource
from .us_index_sources import CboeSp500Source, NasdaqNdxSource
from .verify import CueTableVerifier
from .yahoo_source import YahooChartSource, YahooGate

CUES_FOLDER = storage.REPOSITORY / "research" / "data" / "global-cues"
CHECKS_FOLDER = CUES_FOLDER / "checks"
SNAPSHOT_LOG_FOLDER = storage.MANIFEST_FOLDER / "global-cues"  # one row per archived copy, like the manifests
REVISIONS_FILE = "revisions.csv"  # the public cues' shared revision log
CLOSURES_FILE = CUES_FOLDER / "us_market_closures.csv"  # NYSE's unscheduled whole-day closures, each sourced
TRADING_DATES_FILE = CUES_FOLDER / "us_trading_dates.csv"  # dates only, from the Drive-only index tables
BEHIND_EPISODES = CHECKS_FOLDER / "behind_alerted.txt"  # names only (judge 351 add. 2)
PRIVATE_FOLDER = "global-cues"  # in Drive's derived area: <cue>/rows, <cue>/revisions, <cue>/checks
YAHOO_SUFFIX = "_yahoo"
PREOPEN_INDEXES = ("nikkei225", "kospi", "asx200", "taiex", "hang_seng", "sse_composite", "sti")  # open by 08:50 IST
PREOPEN_TABLE = "preopen"
TWSE_CLOSURES_FILE = storage.CALENDAR_FOLDER / "twse_closures.csv"  # A17f: TWSE's published and unscheduled closures
PREOPEN_COMMIT = "A17e: {what} (receipts)"
BEHIND_NAMES = (CboeSp500Source.cue, RbiUsdInrSource.cue, "nasdaq100", "vix_us")  # NYSE or NSE session calendars
# A17e: (index, Yahoo symbol, market, max age in days, the official cue or None); max age covers each market's longest
# usual closure (China's October and New Year weeks: 10 days)
WORLD_INDEXES = (
    ("nikkei225", "^N225", TOKYO, 7, NikkeiSource.cue),
    (
        "kospi",
        "^KS11",
        SEOUL,
        10,
        None,
    ),  # 10: Chuseok closed 2-9 Oct 2025  # KRX's own API needs the owner's key (A17e amendment 2)
    ("asx200", "^AXJO", SYDNEY, 7, None),
    ("hang_seng", "^HSI", HONG_KONG, 7, None),
    ("sse_composite", "000001.SS", SHANGHAI, 10, CsindexShanghaiSource.cue),
    ("sti", "^STI", SINGAPORE, 7, None),
    ("taiex", "^TWII", TAIPEI, 10, TwseTaiexSource.cue),  # 10: the Lunar New Year
    ("ftse100", "^FTSE", LONDON, 5, None),
    ("dax", "^GDAXI", FRANKFURT, 5, "dax"),
    ("eurostoxx50", "^STOXX50E", EURO_STOXX, 5, "eurostoxx50"),
    ("vix_us", "^VIX", CBOE_VIX, 4, CboeVixSource.cue),
    ("nasdaq100", "^NDX", NEW_YORK, 4, NasdaqNdxSource.cue),  # Nasdaq's own close is a day late at 03:41 (resp. 298)
)
YAHOO_GATE = YahooGate()  # one per process, so one per run: the first Yahoo block stops every Yahoo cue after it
INDEX_PAIRS = {index: IndexPair(official, index + YAHOO_SUFFIX) for index, *_, official in WORLD_INDEXES}
US_AND_RUPEE_SOURCES: tuple[GlobalCueSource, ...] = (
    CboeSp500Source(),
    NasdaqNdxSource(),
    TreasuryTenYearSource(),
    EiaBrentSource(),
    RbiUsdInrSource(),
    FbilUsdInrSource(),
)
WORLD_SOURCES: tuple[GlobalCueSource, ...] = (  # A17e
    CsindexShanghaiSource(),
    TwseTaiexSource(),
    NikkeiSource(),
    CboeVixSource(),
    StoxxSource("eurostoxx50", "sx5e", "Euro Stoxx 50", EURO_STOXX),
    StoxxSource("dax", "dax", "DAX", FRANKFURT),
    *(
        YahooChartSource(index + YAHOO_SUFFIX, symbol, market, age, official is not None, YAHOO_GATE)
        for index, symbol, market, age, official in WORLD_INDEXES
    ),
)
SOURCES = US_AND_RUPEE_SOURCES + WORLD_SOURCES
DRIVE_SETTINGS_MISSING = f"set {', '.join(storage.OWNER_UPLOAD_SETTINGS)} to archive the global cues in Drive"


def sources_named(names: list[str] | None) -> list[GlobalCueSource]:
    return [s for s in SOURCES if not names or s.cue in names]


def next_nse_session(calendar: SessionCalendar, first: date) -> Callable[[date], date]:
    """The first NSE open after a date (`NseSessionCalendar.next_open`): Monday to Friday before the calendar's first
    day (`first`, 2017; those rows were fetched years later and are `backfilled` either way)."""
    return NseSessionCalendar(calendar, first).next_open


def _after() -> Callable[[date], date]:
    calendar = storage.build_session_calendar()
    return next_nse_session(calendar, calendar.first)


def us_market_closures(path=CLOSURES_FILE) -> list[date]:
    with open(path, encoding="utf-8") as f:
        return [date.fromisoformat(row["date"]) for row in csv.DictReader(f)]


def build_calendars(calendar: SessionCalendar) -> dict[str, CueCalendar | None]:
    """Each cue's calendar for its expected date; None: age only (Brent, a weekly release)."""
    nyse, nse = NyseCalendar(us_market_closures()), NseSessionCalendar(calendar, calendar.first)
    us = (
        CboeSp500Source.cue,
        NasdaqNdxSource.cue,
        CboeVixSource.cue,
        f"vix_us{YAHOO_SUFFIX}",
        f"nasdaq100{YAHOO_SUFFIX}",
    )
    by_cue = {
        **dict.fromkeys(us, nyse),
        TreasuryTenYearSource.cue: WeekdayCalendar(),
        RbiUsdInrSource.cue: nse,
        FbilUsdInrSource.cue: nse,
    }
    # A17e's other markets: Monday to Friday (no foreign holiday lists): a local holiday reads `behind`, never `current`
    world = {s.cue for s in WORLD_SOURCES}
    return {s.cue: by_cue.get(s.cue, WeekdayCalendar() if s.cue in world else None) for s in SOURCES}


def build_reader(include_private: bool = True, env=os.environ) -> CueReader:
    """What every consumer reads a cue through: `reading_for` on the cue's table (private ones need Drive)."""
    tables = build_tables(include_private, env)
    calendars = build_calendars(storage.build_session_calendar())
    return CueReader(tables, {s.cue: s for s in SOURCES if s.cue in tables}, calendars)


def build_behind_check(env=os.environ) -> BehindCheck:
    """Judge 351 add. 2: the names judged `behind` at 09:15 (each with a real session calendar), read through the index
    reading where the name is an index (the official value, or Yahoo's when newer)."""
    indexes = build_index_reader(env=env)

    def read(name: str, day: date) -> CueReading:
        if name in INDEX_PAIRS:
            return indexes.read(name, day, OPEN, live_only=True).reading
        return indexes.reader.read(name, day, OPEN, live_only=True)

    return BehindCheck(read, BEHIND_NAMES, OpenProblems(BEHIND_EPISODES))


def build_preopen(env=os.environ) -> tuple[PreopenReader, list[tuple[str, YahooChartSource]]]:
    """A17e part B: the reader of the Asian levels before 09:15 and the indexes it reads, in order."""
    indexes, yahoo = build_index_reader(env=env), {s.cue: s for s in WORLD_SOURCES}

    def previous_close(index: str, seen_at: datetime) -> tuple[str, str]:
        known = indexes.read(index, seen_at.date(), OPEN, live_only=True)
        return (known.reading.row["value"], known.cue or "") if known.reading.row else ("", "")

    rows = _private_log(env, PREOPEN_TABLE, "rows")
    calendars = {"taiex": ClosureCalendar("TWSE", lambda: load_closures(TWSE_CLOSURES_FILE, TWSE_CLOSURES_FILE.name))}
    settled = frozenset(i for i in PREOPEN_INDEXES if INDEX_PAIRS[i].official)  # A17f rule 3: an official table
    session, raw = _session(), build_raw_area(env)
    log = SnapshotLog(SNAPSHOT_LOG_FOLDER)
    reader = PreopenReader(session, raw, log, rows, previous_close, now_ist, calendars, settled)
    return reader, [(index, yahoo[index + YAHOO_SUFFIX]) for index in PREOPEN_INDEXES]


def nse_session_day(day: date) -> bool:
    """Part B reads only on a day NSE trades in the morning (A7: regular or special, never muhurat-only)."""
    from ..quotes.recorder import RECORDED_SESSION_KINDS

    return storage.build_session_calendar().session_kind(day) in RECORDED_SESSION_KINDS


def build_preopen_committers() -> list[OwnedPathsCommitter]:
    """Part B's own repository files: its snapshot logs and O10's capture-error log (its row after a failure); each
    committer adds only those paths, pulls with --no-rebase and retries its push (A16e's committer)."""
    from ..health.capture_errors import CAPTURE_ERRORS_FILE

    errors = storage.REPOSITORY / CAPTURE_ERRORS_FILE
    logs = [f"{index}_preopen.csv" for index in PREOPEN_INDEXES]
    return [
        OwnedPathsCommitter(
            storage.REPOSITORY, SNAPSHOT_LOG_FOLDER, logs, message=PREOPEN_COMMIT, label="pre-open logs"
        ),
        OwnedPathsCommitter(storage.REPOSITORY, errors.parent, [errors.name], message=PREOPEN_COMMIT, label="O10 row"),
    ]


def build_index_reader(include_private: bool = True, env=os.environ) -> IndexReader:
    """A17e: one reading per world index, the official value where it has the date, Yahoo's otherwise."""
    return IndexReader(build_reader(include_private, env), INDEX_PAIRS)


def _owner_drive(env=os.environ):
    drive = storage.build_owner_drive(env)
    if drive is None:
        raise RuntimeError(DRIVE_SETTINGS_MISSING)
    return drive


def _private_log(env, cue: str, kind: str) -> DrivePartsRowLog:
    """A private cue's rows, revisions or gaps: write-once parts in Drive's derived area (owner decision a927390)."""
    return DrivePartsRowLog(AreaStore(_owner_drive(env), DERIVED_AREA), f"{PRIVATE_FOLDER}/{cue}/{kind}", now_ist)


def build_tables(include_private: bool = True, env=os.environ) -> dict[str, CueTable]:
    """Public cues' tables in the repository; private cues' in Drive (needs the Drive settings)."""
    after, shared_revisions = _after(), CsvRowLog(CUES_FOLDER / REVISIONS_FILE)
    tables = {
        s.cue: CueTable(s.cue, CsvRowLog(CUES_FOLDER / f"{s.cue}.csv"), shared_revisions, after)
        for s in SOURCES
        if not s.private
    }
    for s in SOURCES if include_private else ():
        if s.private:
            tables[s.cue] = CueTable(
                s.cue, _private_log(env, s.cue, "rows"), _private_log(env, s.cue, "revisions"), after
            )
    return tables


def _checks(tables: dict[str, CueTable], env=os.environ) -> CueChecks:
    private = {
        s.cue: DriveSnapshots(AreaStore(_owner_drive(env), DERIVED_AREA), f"{PRIVATE_FOLDER}/{s.cue}/checks", now_ist)
        for s in SOURCES
        if s.private and s.cue in tables
    }
    pairs = {
        index: DriveSnapshots(
            AreaStore(_owner_drive(env), DERIVED_AREA), f"{PRIVATE_FOLDER}/{p.official}/pairs", now_ist
        )
        for index, p in INDEX_PAIRS.items()
        if p.official in tables
    }
    calendars, by_cue = build_calendars(storage.build_session_calendar()), {s.cue: s for s in SOURCES}
    sessions = {
        i: calendars[p.official] for i, p in INDEX_PAIRS.items() if p.official and by_cue[p.official].holiday_rows
    }
    return CueChecks(tables, CHECKS_FOLDER, private, TRADING_DATES_FILE, INDEX_PAIRS, pairs, sessions)


def build_raw_area(env=os.environ) -> RawFileStore:
    return AreaStore(_owner_drive(env), storage.RAW_AREA)


def _session() -> PacedSession:
    from ..rehearsal.cue_wiring import rehearsed_cue_session

    session = rehearsed_cue_session(PacedSession())  # story REH1c: the day's archived copies when rehearsing
    session.headers["User-Agent"] = RESEARCH_USER_AGENT  # who we are, plainly (owner rule 50a79a43: no false identity)
    return session


def build_job(env=os.environ) -> GlobalCueJob:
    session = _session()
    created = GoogleDriveCreationTimes(_owner_drive(env), storage.RAW_AREA)
    collector = CueCollector(session, build_raw_area(env), SnapshotLog(SNAPSHOT_LOG_FOLDER), now_ist, created)
    tables = build_tables(env=env)
    return GlobalCueJob(collector, tables, _checks(tables, env))


def build_checks(env=os.environ) -> CueChecks:
    """The checks from the tables: public ones only when the Drive settings are missing (no network otherwise)."""
    with_drive = storage.build_owner_drive(env) is not None
    tables = build_tables(include_private=with_drive, env=env)
    return _checks(tables, env)


def build_verifier(env=os.environ) -> CueTableVerifier:
    return CueTableVerifier(build_raw_area(env), SnapshotLog(SNAPSHOT_LOG_FOLDER), _after())
