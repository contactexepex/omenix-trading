"""The only code that removes anything from Drive staging (story S1). It is NOT a delete on a store: it takes an
archive path in the staging layout (`<source>/<archive path>/<fetch stamp>`), builds `staging/...` itself from
validated parts, and hard-refuses anything that is not strictly inside `staging/`. It moves the file to Drive's
trash (recoverable for about 30 days), never a permanent delete.

The restriction is in this code, not in credentials: the one Drive credential is shared (as for the promotion gate's
"only it writes the Record"). The Record writers and `RawFileStore` have no delete and are not touched."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from fno.ingestion.promotion.staging import STAMP_FORMAT
from fno.ingestion.storage.google_drive import DRIVE_FILES_URL
from fno.ingestion.storage.google_drive_upload import GoogleDriveUploadStore
from fno.ingestion.storage.raw_store import path_parts

STAGING_ROOT = "staging"
NOT_STAGING = "refused: {path!r} is not strictly inside {root}/"
BAD_STAMP = "refused: {stamp!r} is not a fetch stamp"


class NotStagingPath(ValueError):
    """A path outside `staging/` (or the staging root itself) was handed to the deleter."""


class StagingTrash(ABC):
    @abstractmethod
    def trash(self, source: str, archive_path: str, stamp: str) -> bool:
        """Moves one staged copy to the trash; False when it was already gone. Raises NotStagingPath for anything
        but a staged copy and an error when the move failed (the copy then stays)."""


def staged_name(source: str, archive_path: str, stamp: str) -> str:
    """`staging/<source>/<archive path>/<stamp>`, from parts that are valid archive paths and a real fetch stamp."""
    try:
        datetime.strptime(stamp, STAMP_FORMAT)
    except ValueError:
        raise NotStagingPath(BAD_STAMP.format(stamp=stamp)) from None
    full = f"{STAGING_ROOT}/{source}/{archive_path}/{stamp}"
    return inside_staging(full)


def inside_staging(full_path: str) -> str:
    """The path itself when it is strictly inside `staging/`, else NotStagingPath. Compares whole path parts, so
    `staging2/x`, `Staging/x`, `staging` alone, `raw/x` and `staging/../raw/x` are all refused."""
    try:
        parts = path_parts(full_path)
    except ValueError:
        raise NotStagingPath(NOT_STAGING.format(path=full_path, root=STAGING_ROOT)) from None
    if parts[0] != STAGING_ROOT or len(parts) < 2:
        raise NotStagingPath(NOT_STAGING.format(path=full_path, root=STAGING_ROOT))
    return full_path


class DriveStagingTrash(StagingTrash):
    def __init__(self, drive: GoogleDriveUploadStore):
        """`drive`: the whole project folder, signed in as the owner."""
        self.drive = drive

    def trash(self, source: str, archive_path: str, stamp: str) -> bool:
        return self._trash_path(staged_name(source, archive_path, stamp))

    def _trash_path(self, full_path: str) -> bool:
        inside_staging(full_path)  # again, at the last step before Drive: whatever built the path, this is the gate
        file_id = self.drive.file_id(full_path)
        if file_id is None:
            return False
        self.drive.drive.request(
            "patch", f"{DRIVE_FILES_URL}/{file_id}", json={"trashed": True}, params={"fields": "id"}
        )
        return True
