"""Composition root of the 15-minute recorder (story A16): the only place that picks Groww, the owner's Drive, the
repository folder, the clock servers, the alert sender and the publisher. Swapping the source is one new
`IntradayQuoteSource` class plus one line here.

A dry run reads Groww live but writes the raw snapshots, ledger, realised variance and heartbeat under a local folder
outside the repository, sends no alert and commits nothing."""

from __future__ import annotations

from pathlib import Path

from ..alerts.sender import AlertSender, NoAlertSender
from ..composition import build_alert_sender
from ..forecast_v4.cutoff_move import cutoff_flag
from ..forecast_v4.terms import MOVED_AFTER_CUTOFF_X
from ..models import now_ist
from ..providers.groww import GrowwProvider
from ..quotes.expiry_listing import NseDailyFileExpiries
from ..quotes.monthly_contracts import PointInTimeMonthlies
from ..storage.data_store import new_run_id
from ..storage.manifest_commit import GitManifestRecorder
from ..storage.owned_paths_commit import OwnedPathsCommitter
from ..storage.raw_library import RawFileLibrary
from ..storage.raw_source import NseDailyFoSource
from ..storage.raw_store import AreaStore, LocalFolderStore, RawFileStore
from ..storage.wiring import (
    OWNER_UPLOAD_SETTINGS,
    RAW_AREA,
    REPOSITORY,
    build_nse_source,
    build_owner_drive,
    build_raw_stores,
    build_session_calendar,
)
from .claims import CLAIM_LABEL, CLAIM_MESSAGE, GitMarkClaims, MarkClaims, NoClaims
from .clock_wiring import build_clock_check
from .expiry_plan import UNDERLYING, ExpiryPlan
from .groww_source import GrowwIntradaySource, groww_listed_expiries
from .heartbeat import FILE_NAME, Heartbeat, PublishedHeartbeat
from .ledger import ROOT as LEDGER_ROOT
from .ledger import SlotLedger
from .observer import MarkObserver
from .observer_group import ObserverGroup
from .read_only import ReadOnlyGroww
from .realised_vol import QuoteSnapshotRv15m
from .recorder import IntradayRecorder
from .rv_table import ROOT as RV_ROOT
from .rv_table import RvTable
from .session_rv import SessionRv
from .snapshot_files import SnapshotFiles
from .sync import GitLedgerSync, LedgerSync, NoSync

INTRADAY_FOLDER = REPOSITORY / "research" / "data" / "intraday"  # derived files only: no prices
CLAIMS_FOLDER = REPOSITORY / "receipts" / "intraday" / "claims"  # one claim file per mark (O9 section 6)
DRY_RUN_DRIVE = "drive"  # inside a dry-run folder: stands in for the Drive project folder
COMMIT_MESSAGE, COMMIT_LABEL = "Data: intraday slots ({what})", "intraday files"
DRY_RUN_ALERTS = "dry run"
OWNED_PATHS = (LEDGER_ROOT, RV_ROOT, FILE_NAME)  # the ledger, the session RV and the heartbeat; nothing else (A16e)


def build_intraday_recorder(cfg: dict, dry_run_folder: Path | None = None) -> IntradayRecorder:
    folder = Path(dry_run_folder) if dry_run_folder else INTRADAY_FOLDER
    ledger = SlotLedger(folder)
    files = SnapshotFiles(GrowwIntradaySource.name, _snapshot_store(folder, dry_run_folder is not None), ledger)
    provider = GrowwProvider(cfg)
    client = ReadOnlyGroww(lambda: provider.api)  # the only Groww object the source holds (criterion 10)
    plan = _expiry_plan(groww_listed_expiries(client))
    source = GrowwIntradaySource(client, plan, provider.fallback_lot_size(UNDERLYING))
    calendar = build_session_calendar()
    session_rv = SessionRv(files, calendar, RvTable(folder), QuoteSnapshotRv15m(), cutoff=v4_cutoff_flag)
    alerts = _alerts(dry_run_folder)
    return IntradayRecorder(
        source, files, ledger, Heartbeat(folder), calendar, alerts, build_clock_check(), session_rv,
        _sync(dry_run_folder, alerts), claims=_claims(dry_run_folder), observer=ObserverGroup(_observers()),
    )  # fmt: skip


def _observers() -> tuple[tuple[MarkObserver, float], ...]:
    """Every mark observer with its time limit, in order: LM1's position monitor, then A21's announcements poll, when
    they are built (each owner names its limit here)."""
    return ()


def v4_cutoff_flag(levels: dict) -> tuple[str, str]:
    """Protocol v4's moved-after-cutoff flag and sign at the frozen X (story G10)."""
    return cutoff_flag(levels, MOVED_AFTER_CUTOFF_X)


def build_heartbeat() -> PublishedHeartbeat:
    """What the silence check reads: GitHub's copy on `main`, never this host's own working tree."""
    return PublishedHeartbeat(REPOSITORY, (INTRADAY_FOLDER / FILE_NAME).relative_to(REPOSITORY).as_posix())


def _snapshot_store(folder: Path, dry_run: bool) -> RawFileStore:
    """The owner's Drive `raw` area (A9); in a dry run, a local folder of the same shape. Copies are content-addressed
    (`SnapshotFiles`), so nothing is ever written over and no revisions area is needed."""
    drive = LocalFolderStore(folder / DRY_RUN_DRIVE) if dry_run else build_owner_drive()
    if drive is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to store snapshots in Drive")
    return AreaStore(drive, RAW_AREA)


def _expiry_plan(listed) -> ExpiryPlan:
    """Groww's list first; NSE's daily files for what Groww cannot list and to prove the monthly (as A4). Read only:
    a file not yet in Drive is fetched from NSE but never archived here (the 3 pm recorder's library does that), so
    no run, dry or live, writes to Drive or the repository's manifests through this path."""
    nse = NseDailyFileExpiries(RawFileLibrary(build_raw_stores(), build_nse_source(NseDailyFoSource)))  # read only
    return ExpiryPlan(listed, nse, PointInTimeMonthlies(nse))


def _alerts(dry_run_folder: Path | None) -> AlertSender:
    return NoAlertSender(DRY_RUN_ALERTS) if dry_run_folder else build_alert_sender()


def _claims(dry_run_folder: Path | None) -> MarkClaims:
    """One taker per mark across overlapping runs (O9 section 6); a dry run claims nothing."""
    if dry_run_folder:
        return NoClaims()
    committer = GitManifestRecorder(REPOSITORY, CLAIMS_FOLDER, message=CLAIM_MESSAGE, label=CLAIM_LABEL,
                                    keep_remote_on_conflict=True, run_paths=_ledger_paths())  # fmt: skip
    return GitMarkClaims(CLAIMS_FOLDER, committer, new_run_id(), now_ist)


def _sync(dry_run_folder: Path | None, alerts: AlertSender) -> LedgerSync:
    if dry_run_folder:
        return NoSync()
    committer = OwnedPathsCommitter(REPOSITORY, INTRADAY_FOLDER, OWNED_PATHS, message=COMMIT_MESSAGE,
                                    label=COMMIT_LABEL, keep_remote_on_conflict=True,
                                    run_paths=(_repository_path(CLAIMS_FOLDER) + "/",))  # fmt: skip
    return GitLedgerSync(committer, alerts)


def _ledger_paths() -> tuple[str, ...]:
    """The run's ledger, RV and heartbeat paths: the claims committer pushes them with its own (judge 247)."""
    folder = _repository_path(INTRADAY_FOLDER)
    return tuple(f"{folder}/{name}" for name in OWNED_PATHS)


def _repository_path(path: Path) -> str:
    return path.relative_to(REPOSITORY).as_posix()
