"""When a store says it first held a file (story A17b): the check behind adopting a copy whose fetch time is read
from its own path. A store that cannot say answers None, and the caller refuses."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from .google_drive import GoogleDriveStore

CREATED_FIELD = "createdTime"


class CreationTimes(ABC):
    @abstractmethod
    def created_at(self, path: str) -> datetime | None:
        """When the store first held the file at this path; None when absent or unknown."""


class GoogleDriveCreationTimes(CreationTimes):
    """Drive's own `createdTime` of a file, under an area folder of the Drive project folder (e.g. `raw`)."""

    def __init__(self, drive: GoogleDriveStore, area: str):
        self.drive, self.area = drive, area

    def created_at(self, path: str) -> datetime | None:
        found = self.drive.metadata(f"{self.area}/{path}", CREATED_FIELD)
        stamp = (found or {}).get(CREATED_FIELD)
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")) if stamp else None
