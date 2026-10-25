"""Composition root of the filings archive (story A12): the only place that picks the concrete exchange lists, sources
and stores for filings. Swapping NSE for BSE, or Drive for another store, changes this file only.
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import date

from ..market_read_models.nse_files import read_nifty500_list
from ..models import now_ist
from ..providers.public import PublicData
from ..storage import wiring as storage
from ..storage.coverage import CoverageDataset
from ..storage.index_store import DriveIndexStore
from ..storage.librarian import RawDataLibrarian
from ..storage.manifest_folder import FingerprintingStore
from ..storage.raw_store import AreaStore, RawFileStore, StoredCopyDamaged
from ..storage.snapshot_source import EquityListSource, Nifty500ListSource, SnapshotSource
from .archive import FilingArchive
from .coverage import FilingsCoverage
from .day_lists import EveryDayCalendar, check_day_list
from .gaps import GapLog
from .index import (
    NseInsuranceResultsIndex,
    NseIntegratedResultsIndex,
    NseLegacyResultsIndex,
    NseShareholdingIndex,
)
from .librarian import FilingsLibrarian
from .listing_dates import read_listing_dates
from .manifest import FilingManifest
from .progress import ProgressRecord
from .results_table import ResultsTable
from .sources import NseAnnouncementsSource, NseBoardMeetingsSource, NseFilingFileSource

FILINGS_MANIFEST_FOLDER = storage.MANIFEST_FOLDER / "filings"
GAPS_FILE = FILINGS_MANIFEST_FOLDER / "gaps.csv"
INDEX_AREA = "index"  # Drive area for files a job rewrites (progress, symbol map); never under `raw`
SYMBOL_MAP_PATH = "nse/equities/filings/symbols.csv"
NIFTY500_SNAPSHOT_DAY = date(2026, 10, 13)  # the archived Nifty 500 and NSE equity lists the coverage reads (P6)
DAY_LIST_SOURCES = (NseAnnouncementsSource, NseBoardMeetingsSource)
DAY_LISTS = {s.dataset.rsplit("/", 1)[-1]: s for s in DAY_LIST_SOURCES}
UPLOAD_SETTINGS_MISSING = f"set {', '.join(storage.OWNER_UPLOAD_SETTINGS)} to upload to Drive"


def build_filings_manifest() -> FilingManifest:
    return FilingManifest(FILINGS_MANIFEST_FOLDER)


def _owner_raw_area() -> RawFileStore:
    drive = storage.build_owner_drive()
    if drive is None:
        raise RuntimeError(UPLOAD_SETTINGS_MISSING)
    return AreaStore(drive, storage.RAW_AREA)


def build_filings_librarian(log=print) -> FilingsLibrarian:
    """NSE's filing lists and XBRL files into the owner's Drive, each file with its manifest row."""
    indexes = build_filing_indexes()
    archive = FilingArchive(_owner_raw_area(), build_filings_manifest(), now_ist)
    return FilingsLibrarian(indexes, storage.build_nse_source(NseFilingFileSource), archive, now_ist, log)


def build_filing_indexes() -> tuple:
    """NSE's filing lists, through the shared polite session (the librarian's and the probe's)."""
    get_json = PublicData().nse_json
    lists = (NseLegacyResultsIndex, NseInsuranceResultsIndex, NseIntegratedResultsIndex, NseShareholdingIndex)
    return tuple(index(get_json) for index in lists)


def build_day_list_librarian(name: str, log=print) -> RawDataLibrarian:
    """One all-company day list (a key of DAY_LISTS) into the owner's Drive, with its manifest row per day."""
    source_type = DAY_LISTS[name]
    manifests = storage.build_manifest_folder()
    store = FingerprintingStore(_owner_raw_area(), manifests, DAY_LIST_SOURCES)
    dataset = CoverageDataset(source_type, check_day_list, manifests.fingerprints(source_type))
    source = storage.build_nse_source(source_type)
    return RawDataLibrarian(store, source, dataset, EveryDayCalendar(), {}, log)


def build_companies() -> list[str]:
    """The Nifty 500's symbols from the archived list in Drive."""
    return sorted(read_nifty500_list(_archived_list(Nifty500ListSource), Nifty500ListSource.FILENAME))


def build_listing_dates() -> dict[str, date]:
    """Each company's date of listing on NSE, from the archived equity list of the same day (judge 51 addendum 8)."""
    return read_listing_dates(_archived_list(EquityListSource), EquityListSource.FILENAME)


def _archived_list(source: type[SnapshotSource]) -> bytes:
    """An archived NSE list of NIFTY500_SNAPSHOT_DAY, checked against that day's manifest row (the same file name is
    archived every day, so a later day's SHA-256 must not be the one checked). Read with the owner sign-in when its
    settings are there (the scheduled job has them), else with the service account."""
    path = source.path_for(NIFTY500_SNAPSHOT_DAY)
    reader = _owner_raw_area() if storage.build_owner_drive() else storage.build_drive_reader()
    data = reader.get(path)
    rows = storage.build_manifest_folder().read(source)
    want = next((f.sha256 for f in rows if f.day == NIFTY500_SNAPSHOT_DAY), None)
    if data is None or hashlib.sha256(data).hexdigest() != want:
        raise StoredCopyDamaged(f"{path}: missing in Drive or not the manifest's SHA-256")
    return data


def build_filings_coverage() -> FilingsCoverage:
    return FilingsCoverage(storage.build_drive_reader(), build_filings_manifest(), GapLog(GAPS_FILE).read())


def build_results_table() -> ResultsTable:
    """Reported results as known at a moment, read only from Drive (service account)."""
    return ResultsTable(build_filings_manifest(), storage.build_drive_reader())


def build_gap_log() -> GapLog:
    return GapLog(GAPS_FILE)


def _index_area() -> DriveIndexStore:
    drive = storage.build_owner_drive()
    if drive is None:
        raise RuntimeError(UPLOAD_SETTINGS_MISSING)
    return DriveIndexStore(drive, INDEX_AREA)


def build_progress() -> ProgressRecord:
    """The work queue and what each step has finished, from the progress file in Drive's index area."""
    return ProgressRecord(_index_area())


def write_symbol_map() -> None:
    """`index/nse/equities/filings/symbols.csv`: each company's symbol, ISIN and name from the archived Nifty 500
    list, so a symbol NSE renames later still leads to its history (rewritten only when it changes)."""
    rows = csv.DictReader(io.StringIO(_archived_list(Nifty500ListSource).decode("utf-8-sig")))
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(("symbol", "isin", "company_name", "source"))
    source = Nifty500ListSource.path_for(NIFTY500_SNAPSHOT_DAY)
    writer.writerows((r["Symbol"], r["ISIN Code"], r["Company Name"], source) for r in rows)
    index, data = _index_area(), out.getvalue().encode()
    if index.get(SYMBOL_MAP_PATH) != data:
        index.replace(SYMBOL_MAP_PATH, data)
