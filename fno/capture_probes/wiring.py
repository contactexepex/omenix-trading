"""Composition root of the market school's P0b capture probes (story MS-P0b): the live day (Groww through A16's
`ReadOnlyGroww` over `GrowwProvider`, NSE through the honest GET, A20a's dated lots from stored files, O9's data
store, the owned-paths committer, #fno-desk alerts and the O10 log) and the dry run (made-up answers, a jumping clock,
everything written under one folder, nothing pushed or posted)."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from ..alerts.sender import NoAlertSender
from ..health.capture_errors import CAPTURE_ERRORS_FILE, CaptureErrorLog
from ..models import now_ist
from ..storage.data_store import DataStore, new_run_id
from ..storage.raw_store import LocalFolderStore
from ..storage.receipts import ReceiptFolder
from ..storage.wiring import REPOSITORY
from .archive import SlotArchive
from .constants import COMMIT_LABEL, COMMIT_MESSAGE, COUNTS_FOLDER, DRIVE_AREA, MIN_GAP_SECONDS, WRITER, Source
from .counts import CountsFolder
from .day import ProbeDay
from .dry_run import JumpingClock, MadeUpGroww, MadeUpNse, made_up_lot
from .groww_reader import GrowwAnswers, GrowwReader
from .nse_reader import NseGet, NseReader
from .pace import StudyPace
from .publish import GitPublisher, NoPublish, RepoPathsCommitter
from .slot import SlotRunner, SlotTools
from .stops import StopRecorder

DRY_RUN_ALERTS = "dry run"
RECEIPTS_AREA = "receipts/data/" + DRIVE_AREA + "/"


def build_probe_day(cfg: dict) -> ProbeDay:
    """The live probe: reads Groww and NSE at the study pace and pushes only its own records."""
    from ..composition import build_alert_sender
    from ..intraday.read_only import ReadOnlyGroww
    from ..providers import get_provider
    from ..storage.data_wiring import build_data_store
    from ..storage.trading_days import is_trading_day
    from ..storage.wiring import build_session_calendar

    provider = get_provider("groww", cfg)  # GW1a: the sign-in guard and the 60 s pause after a 429 come with it
    client = ReadOnlyGroww(lambda: provider.api)
    lot = _archived_lot()
    groww = GrowwReader(client, GrowwAnswers(groww_rate_limited), lot, now_ist)
    owned = (RECEIPTS_AREA, COUNTS_FOLDER + "/", CAPTURE_ERRORS_FILE)
    committer = RepoPathsCommitter(REPOSITORY, owned, message=COMMIT_MESSAGE, label=COMMIT_LABEL)
    stops = StopRecorder(build_alert_sender(), CaptureErrorLog(REPOSITORY / CAPTURE_ERRORS_FILE))
    tools = SlotTools(groww, NseReader(NseGet(), lot, now_ist), _paces(time.monotonic, time.sleep), now_ist,
                      time.monotonic, time.sleep, SlotArchive(build_data_store(WRITER), DRIVE_AREA),
                      CountsFolder(REPOSITORY / COUNTS_FOLDER), GitPublisher(committer), stops)  # fmt: skip
    calendar = build_session_calendar()
    return ProbeDay(lambda day: is_trading_day(calendar, day), tools.folder, SlotRunner(tools), now_ist, time.sleep)


def build_dry_run_day(session: date, folder: Path) -> ProbeDay:
    """The same day over made-up answers; Drive, receipts and counts under `folder`; no alert, push or O10 row."""
    clock = JumpingClock(session)
    store = DataStore(LocalFolderStore(folder / "drive"), "data", ReceiptFolder(folder / "receipts"), WRITER,
                      new_run_id())  # fmt: skip
    never_limited = GrowwAnswers(lambda error: False)  # made-up answers are never rate-limited
    tools = SlotTools(GrowwReader(MadeUpGroww(clock, session), never_limited, made_up_lot, clock.wall),
                      NseReader(NseGet(MadeUpNse(clock, session)), made_up_lot, clock.wall),
                      _paces(clock.timer, clock.sleep), clock.wall, clock.timer, clock.sleep,
                      SlotArchive(store, DRIVE_AREA), CountsFolder(folder / "counts"), NoPublish(),
                      StopRecorder(NoAlertSender(DRY_RUN_ALERTS), None))  # fmt: skip
    return ProbeDay(lambda day: True, tools.folder, SlotRunner(tools), clock.wall, clock.sleep)


def _paces(timer: Callable[[], float], sleep) -> dict[Source, StudyPace]:
    return {source: StudyPace(MIN_GAP_SECONDS[source], timer, sleep) for source in Source}


def _archived_lot():
    """A20a's dated lot for today's session from stored files (MS-P1b's reader), or None: never a guessed lot."""
    from ..school.roads.lots import ArchivedLots
    from ..school.roads.stored_files import StoredFilesOnly
    from ..school.roads.wiring import build_archive_stores
    from ..storage.raw_library import RawFileLibrary

    lots = ArchivedLots(RawFileLibrary(build_archive_stores(), StoredFilesOnly()))

    def lot(underlying: str, expiry: date) -> int | None:
        found = lots.lot(underlying, now_ist().date(), (expiry,))
        return getattr(found, "units", None)

    return lot


def groww_rate_limited(error: Exception) -> bool:
    """The project's one 429 detector (story GW1, parts 3-4), never a copy: a 429 in either SDK form, or GW1's
    unsent pause within 60 s after one."""
    from ..providers.groww_rate_guard import GrowwRateLimitPaused, is_rate_limit

    return is_rate_limit(error) or isinstance(error, GrowwRateLimitPaused)
