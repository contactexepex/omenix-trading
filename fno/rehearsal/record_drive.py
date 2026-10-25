"""The real record's raw files, read-only and signed in to at the first read (story REH1c): a recorded source can be
built, and the guard can check it, without Drive; a read without Drive's settings says which are missing."""

from __future__ import annotations

NO_DRIVE = "rehearsal: the recorded answers are in the owner's Drive; set its four FNO_GDRIVE_* settings"


class RecordFiles:
    def __init__(self, area: str):
        self.area, self._store = area, None

    def __call__(self, path: str) -> bytes | None:
        if self._store is None:
            from ..storage.raw_store import AreaStore
            from ..storage.wiring import build_owner_drive

            drive = build_owner_drive()
            if drive is None:
                raise RuntimeError(NO_DRIVE)
            view = drive.record_view()
            self._store = AreaStore(view, self.area) if self.area else view
        return self._store.get(path)
