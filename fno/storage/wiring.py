"""Composition root for raw data: the only place that picks concrete stores and sources (the app's services are
wired in fno/composition.py). Swapping Google Drive or NSE for something else changes this file only."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from ..constants import (
    ENV_GDRIVE_FOLDER_ID,
    ENV_GDRIVE_OAUTH_CLIENT_ID,
    ENV_GDRIVE_OAUTH_CLIENT_SECRET,
    ENV_GDRIVE_OAUTH_REFRESH_TOKEN,
    ENV_GDRIVE_SERVICE_ACCOUNT_JSON,
    PANEL_FORMAT_LEGACY,
    PANEL_FORMAT_UDIFF,
    PANEL_INDEX_CLOSE,
    RESEARCH_USER_AGENT,
)
from ..http_pacing import PacedSession
from ..research_data.calendar import SessionCalendar, load_session_calendar
from ..research_data.nifty_panel import DailyFiles
from ..research_data.panel_store import CsvGzPanelFolder, PanelSink
from .content_checks import COVERED_SESSION, VALIDATORS
from .coverage import CoverageCheck, CoverageDataset, read_exceptions
from .google_drive import GoogleDriveStore, service_account_token
from .google_drive_upload import GoogleDriveUploadStore
from .librarian import RawDataLibrarian
from .manifest_commit import GitManifestRecorder, ManifestRecorder
from .manifest_folder import FingerprintingStore, ManifestFolder
from .owner_token import OwnerAccessToken
from .raw_library import FileLibrary, RawFileLibrary, StoredFilesLibrary
from .raw_source import (
    NseArchiveSource,
    NseDailyFoSource,
    NseIndexCloseSource,
    NseLegacyFoSource,
    ParticipantOiSource,
)
from .raw_store import AreaStore, LocalFolderStore, RawFileStore
from .revision_source import RevisionCapturingSource
from .revisions import RevisionArchive, RevisionIndex
from .session_filed_taker import CurrentSessionTaker, SessionFiledTaker
from .snapshot_source import (
    CorporateActionsBySymbolSource,
)
from .snapshot_taker import SnapshotTaker
from .source_lists import DATED_SOURCES, LIBRARIAN_DATASETS, RAW_SOURCES, SNAPSHOT_DATASETS
from .source_lists import FINGERPRINT_SOURCES as FINGERPRINT_SOURCES  # re-exported: callers read them from here
from .source_lists import RUN_DATED_FLOWS as RUN_DATED_FLOWS
from .source_lists import SNAPSHOT_SOURCES as SNAPSHOT_SOURCES
from .trading_days import next_trading_day
from .versioned_store import VersionedRawStore

RAW_AREA = "raw"  # original downloads; other kinds of files get their own area next to it
REVISIONS_AREA = "revisions"  # later versions NSE published of raw files, under the same paths (A11)
CALENDAR_FOLDER = Path(__file__).resolve().parents[2] / "research" / "data" / "calendar"
CALENDAR_FILE = CALENDAR_FOLDER / "nse_sessions.csv"  # NSE's sessions, from its circulars (SessionCalendar)
COVERAGE_EXCEPTIONS = CALENDAR_FOLDER / "exceptions.csv"
REPOSITORY = Path(__file__).resolve().parents[2]
MANIFEST_FOLDER = REPOSITORY / "research" / "data" / "manifests"  # SHA-256 per file (A10)
REVISION_INDEX_FOLDER = MANIFEST_FOLDER / "revisions"  # one row per archived later version (A11)


def build_raw_stores(project_folder: Path | None = None, token_for=service_account_token) -> list[RawFileStore]:
    """Where raw files are looked for, in order: the `raw` area of a local (Drive-synced) project folder, then of the
    shared Google Drive project folder if set up."""
    stores: list[RawFileStore] = [AreaStore(LocalFolderStore(project_folder), RAW_AREA)] if project_folder else []
    drive = _service_account_drive(token_for)
    if drive is not None:
        stores.append(AreaStore(drive, RAW_AREA))
    return stores


def _service_account_drive(token_for=service_account_token) -> GoogleDriveStore | None:
    """The shared Drive project folder, read with the service account; None unless both settings are set."""
    key, folder = os.environ.get(ENV_GDRIVE_SERVICE_ACCOUNT_JSON), os.environ.get(ENV_GDRIVE_FOLDER_ID)
    return GoogleDriveStore(folder, lambda: token_for(key)) if key and folder else None


OWNER_UPLOAD_SETTINGS = (
    ENV_GDRIVE_FOLDER_ID,
    ENV_GDRIVE_OAUTH_CLIENT_ID,
    ENV_GDRIVE_OAUTH_CLIENT_SECRET,
    ENV_GDRIVE_OAUTH_REFRESH_TOKEN,
)


def build_owner_drive_store(env=os.environ, session=None) -> RawFileStore | None:
    """The `raw` area of the Drive project folder, written as the owner (story A9); None unless all four settings
    are set. Signs in at once, so an expired consent shows up here as DriveSignInRefused."""
    drive = build_owner_drive(env, session)
    if drive is None:
        return None
    raw = AreaStore(drive, RAW_AREA)
    return FingerprintingStore(raw, build_manifest_folder(), RAW_SOURCES)  # every saved file gets its manifest row


def build_owner_drive(env=os.environ, session=None) -> GoogleDriveUploadStore | None:
    """The whole Drive project folder written as the owner (no area, no manifest); None unless all four settings."""
    folder, client_id, client_secret, refresh_token = (env.get(name) for name in OWNER_UPLOAD_SETTINGS)
    if not (folder and client_id and client_secret and refresh_token):
        return None
    return GoogleDriveUploadStore(folder, OwnerAccessToken(client_id, client_secret, refresh_token), session)


def build_revision_index() -> RevisionIndex:
    return RevisionIndex(REVISION_INDEX_FOLDER, RAW_SOURCES)  # every dataset with a manifest; snapshots have none


def build_revision_archive(env=os.environ, session=None) -> RevisionArchive:
    """Later NSE versions of raw files, saved to the owner's Drive `revisions` area with an index row (story A11)."""
    drive = build_owner_drive(env, session)
    if drive is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to archive revisions in Drive")
    raw, revisions = AreaStore(drive, RAW_AREA), AreaStore(drive, REVISIONS_AREA)
    return RevisionArchive(raw, revisions, build_revision_index(), build_manifest_folder())


def build_revision_capturing_source(
    source_type: type[NseArchiveSource], archive: RevisionArchive
) -> RevisionCapturingSource:
    """One NSE dataset whose every full read is offered to the revision archive (A8's sweep, data-revisions)."""
    return RevisionCapturingSource(build_nse_source(source_type), archive)


def build_versioned_reader(as_of: datetime | None = None) -> VersionedRawStore:
    """Raw files in Drive with their revisions: the version available at `as_of` for research, or NSE's newest one we
    hold when `as_of` is None, for publishing (story A11). Read with the service account, else with the owner's own
    sign-in (GitHub Actions has only the owner's secrets: market-publish.yml)."""
    drive = _service_account_drive() or build_owner_drive()
    if drive is None:
        raise RuntimeError(f"set {ENV_GDRIVE_SERVICE_ACCOUNT_JSON} or {', '.join(OWNER_UPLOAD_SETTINGS)} to read Drive")
    raw, revisions = AreaStore(drive, RAW_AREA), AreaStore(drive, REVISIONS_AREA)
    return VersionedRawStore(raw, revisions, build_revision_index(), as_of)


def build_manifest_folder() -> ManifestFolder:
    return ManifestFolder(MANIFEST_FOLDER)


def build_manifest_recorder() -> ManifestRecorder:
    """Commits the manifest rows of this repository (git, with its hooks)."""
    return GitManifestRecorder(REPOSITORY, MANIFEST_FOLDER)


def build_nse_library(source_type: type[NseArchiveSource], project_folder: Path | None = None) -> RawFileLibrary:
    """One NSE dataset: from the stores if they have it, else from NSE. What it fetches is archived straight to the
    owner's Drive when the upload settings exist, else under the local project folder's `raw` area if given."""
    archive = build_owner_drive_store()
    if archive is None and project_folder:
        archive = AreaStore(LocalFolderStore(project_folder), RAW_AREA)
    return RawFileLibrary(build_raw_stores(project_folder), build_nse_source(source_type), archive)


def build_nse_source(source_type: type[NseArchiveSource]) -> NseArchiveSource:
    """One NSE dataset straight from NSE's archive, through the shared polite session."""
    session = PacedSession()
    session.headers["User-Agent"] = RESEARCH_USER_AGENT  # NSE refuses the default python-requests identity
    return source_type(session)


def build_nse_fo_library(project_folder: Path | None = None) -> RawFileLibrary:
    """NSE daily F&O files in the current (UDiFF) format, January 2024 onwards."""
    return build_nse_library(NseDailyFoSource, project_folder)


def build_nse_legacy_fo_library(project_folder: Path | None = None) -> RawFileLibrary:
    """NSE daily F&O files in the older format, up to 5 July 2024."""
    return build_nse_library(NseLegacyFoSource, project_folder)


def build_nse_index_close_library(project_folder: Path | None = None) -> RawFileLibrary:
    """NSE daily index closing values (NIFTY 50, India VIX and others)."""
    return build_nse_library(NseIndexCloseSource, project_folder)


def build_participant_oi_library(project_folder: Path | None = None) -> RawFileLibrary:
    """NSE daily participant-wise open interest (story A8)."""
    return build_nse_library(ParticipantOiSource, project_folder)


QUOTES_FOLDER = (
    Path(__file__).resolve().parents[2] / "research" / "data" / "quotes"
)  # repository: sidecars and canonical markers; Groww's raw quote files are in Drive only (A4b)


PARTICIPANT_OI_EVIDENCE = Path(__file__).resolve().parents[2] / "research" / "data" / "participant_oi"
PARTICIPANT_OI_RELEASE_LOG = PARTICIPANT_OI_EVIDENCE / "release_checks.csv"  # NSE's release times, committed (A8)
PARTICIPANT_OI_REREADS = PARTICIPANT_OI_EVIDENCE / "release_rereads.csv"  # the daily rewrite re-read, done per due day
PARTICIPANT_OI_LAST_MODIFIED = PARTICIPANT_OI_EVIDENCE / "archive_last_modified_2026-10-13.csv"  # with the download
PARTICIPANT_OI_SWEEPS = PARTICIPANT_OI_EVIDENCE / "last_modified_sweeps.csv"  # write times that moved later (judge 16)


def build_quote_store(folder: Path | None = None) -> RawFileStore:
    """Where the 3 pm quote snapshots are written and read: Groww's raw quote files in Drive only, everything else in a
    repository folder, committed daily (story A4b; wired in quote_wiring.py, as this file is at its size limit)."""
    from .quote_wiring import build_drive_only_quote_store

    return build_drive_only_quote_store(folder or QUOTES_FOLDER)


def coverage_datasets(manifests: ManifestFolder | None = None) -> tuple[CoverageDataset, ...]:
    """Every raw dataset with its content check and its manifest's fingerprints (read now, never cached)."""
    manifests = manifests or build_manifest_folder()
    revisions = build_revision_index()
    return tuple(
        CoverageDataset(s, VALIDATORS[s], manifests.fingerprints(s), revisions.counts(s)) for s in DATED_SOURCES
    )


def build_own_list_taker() -> SnapshotTaker:
    """A symbol's own NSE corporate-action list into the owner's Drive (symbols NSE's range list leaves out)."""
    store = build_owner_drive_store()
    if store is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to upload to Drive")
    source = CorporateActionsBySymbolSource
    return SnapshotTaker(store, build_nse_source(source), VALIDATORS[source])


def build_snapshot_taker(name: str) -> SnapshotTaker | SessionFiledTaker:
    """Today's copy of one reference list or flows report (a key of SNAPSHOT_DATASETS) into the owner's Drive, with
    its manifest row."""
    store = build_owner_drive_store()
    if store is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to upload to Drive")
    source_type = SNAPSHOT_DATASETS[name]
    if source_type in COVERED_SESSION:  # a latest-day report: filed under the session it covers
        parts = (store, build_nse_source(source_type), VALIDATORS[source_type], COVERED_SESSION[source_type])
        if source_type.STALE_REFUSED:  # valid only for its own session, written the evening before (A20a)
            calendar = build_session_calendar()
            return CurrentSessionTaker(*parts, lambda day: next_trading_day(calendar, day))
        return SessionFiledTaker(*parts)
    return SnapshotTaker(store, build_nse_source(source_type), VALIDATORS[source_type])


def build_librarian(name: str, log=print) -> RawDataLibrarian:
    """The librarian for one dataset (a key of LIBRARIAN_DATASETS): NSE's archive into the owner's Drive."""
    store = build_owner_drive_store()
    if store is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to upload to Drive")
    source_type = LIBRARIAN_DATASETS[name]
    dataset = next(d for d in coverage_datasets() if d.source is source_type)
    source = build_nse_source(source_type)
    return RawDataLibrarian(store, source, dataset, build_session_calendar(), build_file_exceptions(), log)


def build_drive_reader() -> RawFileStore:
    """The shared Drive project folder's `raw` area, read with the service account."""
    stores = build_raw_stores()
    if not stores:
        raise RuntimeError(f"set {ENV_GDRIVE_SERVICE_ACCOUNT_JSON} and {ENV_GDRIVE_FOLDER_ID} to read Drive")
    return stores[-1]


def build_coverage_check(store: RawFileStore | None = None) -> CoverageCheck:
    """The coverage check of the shared Drive project folder's `raw` area (read-only), or of the given store."""
    return CoverageCheck(store or build_drive_reader(), build_session_calendar(), build_file_exceptions())


PANEL_FOLDER = Path(__file__).resolve().parents[2] / "research" / "data" / "nifty-panel"  # story A3's output
EVENTS_FILE = Path(__file__).resolve().parents[2] / "research" / "data" / "events" / "events.csv"  # story A6
LIVE_VALIDATION_FOLDER = Path(__file__).resolve().parents[2] / "research" / "live_validation"  # story B7 reports


def daily_files(label: str, source_type: type[NseArchiveSource], library: FileLibrary) -> DailyFiles:
    """A day's original file name and bytes from a library: a writer's fetches what no store has from NSE and archives
    it; a reader's (`StoredFilesLibrary`) only reads the stores."""
    return DailyFiles(
        label,
        source_type.dataset,
        source_type.first_day,
        source_type.last_day,
        lambda day: (source_type.filename_for(day), library.get(source_type.path_for(day)).data),
    )


def build_nifty_panel_files(project_folder: Path | None = None) -> tuple[list[DailyFiles], DailyFiles]:
    """The NIFTY panel's inputs: F&O files in order of precedence (current format first), and index closes."""
    fo_files = [
        daily_files(PANEL_FORMAT_UDIFF, NseDailyFoSource, build_nse_fo_library(project_folder)),
        daily_files(PANEL_FORMAT_LEGACY, NseLegacyFoSource, build_nse_legacy_fo_library(project_folder)),
    ]
    return fo_files, build_index_close_files(project_folder)


def build_index_close_files(project_folder: Path | None = None) -> DailyFiles:
    """NSE's daily index-close files for a WRITER (the panel, story A10's warm-up closes): a file no store has is
    fetched from NSE and archived to Drive. Readers use `build_stored_index_close_files`."""
    return daily_files(PANEL_INDEX_CLOSE, NseIndexCloseSource, build_nse_index_close_library(project_folder))


def build_stored_index_close_files() -> DailyFiles:
    """NSE's daily index-close files for a READER: the stores only, never NSE and never a Drive write; a day no store
    has reads as None (not archived yet). The librarian (index-closes.yml, the morning routine) is the one writer."""
    return daily_files(PANEL_INDEX_CLOSE, NseIndexCloseSource, StoredFilesLibrary(_reader_raw_stores()))


def _reader_raw_stores(env=os.environ) -> list[RawFileStore]:
    """The raw stores a reader looks in: the service account's (where set), then the owner's Drive raw area read with
    the owner's settings (GitHub's jobs and the routines carry these), each only ever read."""
    drive = build_owner_drive(env)
    return build_raw_stores() + ([AreaStore(drive, RAW_AREA)] if drive is not None else [])


def build_panel_sink(folder: Path | None = None) -> PanelSink:
    return CsvGzPanelFolder(folder or PANEL_FOLDER)


def build_session_calendar() -> SessionCalendar:
    """NSE's sessions from the repository's calendar file: the one answer to "is this day a session"."""
    return load_session_calendar(CALENDAR_FILE)


def build_file_exceptions() -> dict:
    """(dataset, day) -> reason, for sessions with no archived file: never published (A1) or refused content (A23)."""
    return read_exceptions(COVERAGE_EXCEPTIONS)
