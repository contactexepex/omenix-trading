"""Composition root of story A22's morning capture: NSE's two JSON answers through the shared polite session, Groww's
NIFTY and BANKNIFTY 1-minute candles through A16b's source over A16's `ReadOnlyGroww`, A16's checked clock, the
session calendar, O9's Drive data store, O10's capture-error log, the receipt and error committers and the alert;
A22d's open check over the verified Drive cache and the stored index-close files (never NSE)."""

from __future__ import annotations

import time

from ..composition import build_alert_sender
from ..constants import RESEARCH_USER_AGENT
from ..health.capture_errors import CAPTURE_ERRORS_FILE
from ..health.wiring import build_capture_error_log
from ..http_pacing import PacedSession
from ..intraday.candle_source import GrowwCandleSource
from ..intraday.clock_wiring import build_clock_check
from ..intraday.read_only import ReadOnlyGroww
from ..models import now_ist
from ..providers.groww import GrowwProvider
from ..storage.data_store import DataStore
from ..storage.data_wiring import (
    DATA_AREA,
    RECEIPTS_FOLDER,
    RECEIPTS_LABEL,
    RECEIPTS_MESSAGE,
    build_data_store,
    build_drive_cache,
    receipt_folder,
)
from ..storage.manifest_commit import GitManifestRecorder
from ..storage.owned_paths_commit import OwnedPathsCommitter
from ..storage.trading_days import is_trading_day
from ..storage.wiring import REPOSITORY, build_session_calendar, build_stored_index_close_files
from .check_files import DriveCacheFiles
from .open_check import OpenCheck
from .parts import GrowwIndexPreopen, NseGiftNifty, NsePreopenList, PreopenPart
from .record import JOB, PreopenRecorder
from .run import PreopenRun

GROWW_SYMBOLS = {"nifty": "NSE-NIFTY", "banknifty": "NSE-BANKNIFTY"}  # BANKNIFTY's probed 21 Oct (step 0b)
ERRORS_MESSAGE = "Capture errors: A22 pre-open ({what})"


def build_preopen_recorder(cfg: dict) -> PreopenRecorder:
    calendar = build_session_calendar()
    parts = _parts(cfg)
    clock, store = build_clock_check(), build_data_store(JOB)
    return PreopenRecorder(
        lambda day: is_trading_day(calendar, day),
        lambda finished: PreopenRun(parts, now_ist, time.sleep, finished),
        store, build_capture_error_log(), (_errors_committer(), _receipts_committer()),
        build_alert_sender(), clock.check, _receipts_committer(),
        _open_check(calendar.previous_session, store),
    )  # fmt: skip


def _open_check(previous_session, store: DataStore) -> OpenCheck:
    files = DriveCacheFiles(build_drive_cache(), receipt_folder(), DATA_AREA)
    closes = build_stored_index_close_files()  # the stores only: a day not archived yet reads as None
    return OpenCheck(previous_session, files, lambda day: closes.get(day)[1], store)


def _parts(cfg: dict) -> list[PreopenPart]:
    session = PacedSession()
    session.headers["User-Agent"] = RESEARCH_USER_AGENT  # NSE refuses the default python-requests identity
    provider = _LazyGroww(cfg)
    api = ReadOnlyGroww(lambda: provider.api)  # the only Groww object the capture holds
    indices = [GrowwIndexPreopen(name, _candles(api, symbol)) for name, symbol in GROWW_SYMBOLS.items()]
    from ..rehearsal.preopen_wiring import rehearsed_preopen_parts

    parts = [NseGiftNifty(session, now_ist), NsePreopenList(session, now_ist), *indices]
    return rehearsed_preopen_parts(parts)  # story REH1c: the day's recorded answers when rehearsing


class _LazyGroww:
    """Builds Groww's provider at the first read, not at wiring: the SDK (requirements-groww.txt) is then needed only
    by a live read, where its absence is a named part failure (`CandleCallFailed`), never a crash at start."""

    def __init__(self, cfg: dict):
        self.cfg, self._provider = cfg, None

    @property
    def api(self):
        self._provider = self._provider or GrowwProvider(self.cfg)
        return self._provider.api


def _candles(api, symbol: str) -> GrowwCandleSource:
    return GrowwCandleSource(api, now_ist, symbol=symbol)


def _errors_committer() -> OwnedPathsCommitter:
    """First: the receipts are new files, so they never block its pull; the error log may have changed upstream."""
    folder, name = CAPTURE_ERRORS_FILE.rsplit("/", 1)
    return OwnedPathsCommitter(REPOSITORY, REPOSITORY / folder, [name], message=ERRORS_MESSAGE, label="capture errors",
                               run_paths=(f"{RECEIPTS_FOLDER}/",))  # fmt: skip


def _receipts_committer() -> GitManifestRecorder:
    """O9's receipt committer, which also carries an error-log commit whose own push failed."""
    return GitManifestRecorder(REPOSITORY, REPOSITORY / RECEIPTS_FOLDER, message=RECEIPTS_MESSAGE,
                               label=RECEIPTS_LABEL, run_paths=(CAPTURE_ERRORS_FILE,))  # fmt: skip
