"""Composition root of `fno/school/roads/` (story MS-P1b): the road catalogue and the snapshot source over the recorded
3 pm captures. Every file is read from stored places (the repository's sidecars and markers, the hash-checked Drive
quote store, A20a's archived lot file, NSE's archived F&O files); nothing is fetched from NSE or Groww."""

from dataclasses import dataclass
from pathlib import Path

from ...quotes.expiry_listing import NseDailyFileExpiries
from ...quotes.monthly_contracts import PointInTimeMonthlies
from ...quotes.recorder import DATASET
from ...quotes.weekly import WEEKLY_DATASET
from ...research_data.calendar import SessionCalendar
from ...storage.quote_wiring import build_drive_only_quote_store
from ...storage.raw_library import RawFileLibrary
from ...storage.raw_store import AreaStore, RawFileStore
from ...storage.wiring import (
    OWNER_UPLOAD_SETTINGS,
    QUOTES_FOLDER,
    RAW_AREA,
    build_owner_drive,
    build_raw_stores,
    build_session_calendar,
)
from ..contracts.roads import RoadCatalogue
from ..contracts.snapshot import SnapshotSource
from ..quality.ports import ListedContracts
from .capture import CaptureReader
from .catalogue import RecordedRoadCatalogue
from .expiries import ListedRoadExpiries
from .listed_contracts import NseListedContracts
from .lots import ArchivedLots
from .snapshots import RecordedSnapshotSource
from .stored_files import StoredFilesOnly


class RawFilesNotConfigured(RuntimeError):
    """No Drive setting gives a read of the archived raw files; the roads would all close for a missing file."""


def build_archive_stores() -> list[RawFileStore]:
    """Where NSE's archived files (F&O files, lot files) are read: the service account's Drive, else the owner's."""
    if stores := build_raw_stores():
        return stores
    owner = build_owner_drive()
    if owner is None:
        raise RawFilesNotConfigured(f"set the service-account settings or {', '.join(OWNER_UPLOAD_SETTINGS)}")
    return [AreaStore(owner, RAW_AREA)]


@dataclass(frozen=True)
class RoadServices:
    calendar: SessionCalendar
    catalogue: RoadCatalogue
    snapshots: SnapshotSource
    listing: ListedContracts


def build_road_services(folder: Path = QUOTES_FOLDER, calendar: SessionCalendar | None = None) -> RoadServices:
    """One reader behind both, so a capture is fetched and verified once however often the catalogue and the snapshot
    source ask for it."""
    calendar = calendar or build_session_calendar()
    reader = CaptureReader(
        {dataset: build_drive_only_quote_store(folder, dataset=dataset) for dataset in (DATASET, WEEKLY_DATASET)}
    )
    library = RawFileLibrary(build_archive_stores(), StoredFilesOnly())
    listing = NseDailyFileExpiries(library)
    expiries = ListedRoadExpiries(listing, PointInTimeMonthlies(listing))
    return RoadServices(calendar, RecordedRoadCatalogue(calendar, reader, expiries, ArchivedLots(library)),
                        RecordedSnapshotSource(reader), NseListedContracts(library))  # fmt: skip
