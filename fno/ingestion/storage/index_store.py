"""Index files (story A12): small working files that a job rewrites as it goes, such as a progress record or a
symbol map. They live in their own area (`index`), never in `raw`, because raw files never change and these do.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from fno.ingestion.storage.google_drive_upload import GoogleDriveUploadStore
from fno.ingestion.storage.raw_store import path_parts


class IndexFileStore(ABC):
    @abstractmethod
    def get(self, path: str) -> bytes | None:
        """The file's bytes, or None when there is none yet."""

    @abstractmethod
    def replace(self, path: str, data: bytes) -> None:
        """Writes the file, replacing the previous version (folders made as needed)."""


class DriveIndexStore(IndexFileStore):
    """Index files under one area of the owner's Drive project folder: a new file is created like a raw file; an
    existing one gets new contents in place (same Drive ID, so links to it keep working)."""

    def __init__(self, drive: GoogleDriveUploadStore, area: str):
        path_parts(area)
        self.drive, self.area = drive, area

    def get(self, path: str) -> bytes | None:
        return self.drive.get(f"{self.area}/{path}")

    def replace(self, path: str, data: bytes) -> None:
        file_id = self.drive.file_id(f"{self.area}/{path}")
        if file_id is None:
            self.drive.put(f"{self.area}/{path}", data)
            return
        self.drive.replace_contents(file_id, data)
