"""Drive items with their IDs and creation times, for repairs that must see what the path-based store hides (story
DR1-0): two folders or files with one name in one folder. `GoogleDriveStore` refuses such a name (RawFileConflict);
this adapter lists every copy, so a repair can choose by verified content, and moves or renames an item without ever
deleting one. Signed in as the owner (the same session as the upload store)."""

from __future__ import annotations

from dataclasses import dataclass

from .google_drive import DRIVE_FILES_URL, FOLDER_TYPE
from .google_drive_upload import GoogleDriveUploadStore
from .raw_store import path_parts

ITEMS_QUERY = "'{parent}' in parents and trashed = false"
NAMED_QUERY = ITEMS_QUERY + " and name = '{name}'"
ITEM_FIELDS = "nextPageToken, files(id, name, mimeType, createdTime)"
PAGE_SIZE = 1000


class PathNotFound(LookupError):
    """A folder on the way to the path does not exist."""


class PathAmbiguous(LookupError):
    """A folder on the way to the path (above the repaired one) exists twice: repair that folder first."""


@dataclass(frozen=True)
class DriveItem:
    id: str
    name: str
    folder: bool
    created: str  # Drive's createdTime, UTC ISO 8601

    @classmethod
    def from_answer(cls, item: dict) -> DriveItem:
        return cls(item["id"], item["name"], item["mimeType"] == FOLDER_TYPE, item.get("createdTime", ""))


class DriveItems:
    def __init__(self, store: GoogleDriveUploadStore):
        self.drive, self.root = store.drive, store.folder_id

    def copies(self, path: str) -> tuple[str, list[DriveItem]]:
        """The parent folder's ID and every item named like the path's last part in it, oldest first."""
        *folders, name = path_parts(path)
        parent = self.root
        for part in folders:
            found = [item for item in self._items(parent, part) if item.folder]
            if not found:
                raise PathNotFound(f"no Drive folder {part!r} on the way to {path}")
            if len(found) > 1:
                raise PathAmbiguous(f"{len(found)} Drive folders named {part!r} on the way to {path}")
            parent = found[0].id
        return parent, sorted(self._items(parent, name), key=lambda item: (item.created, item.id))

    def children(self, folder_id: str) -> list[DriveItem]:
        return sorted(self._items(folder_id), key=lambda item: (item.name, item.created, item.id))

    def content(self, item: DriveItem) -> bytes:
        return self.drive.get(f"{DRIVE_FILES_URL}/{item.id}", params={"alt": "media"}).content

    def move(self, item: DriveItem, from_folder: str, to_folder: str) -> None:
        """The same item (ID, bytes and creation time unchanged) in another folder."""
        params = {"addParents": to_folder, "removeParents": from_folder, "fields": "id"}
        self.drive.request("patch", f"{DRIVE_FILES_URL}/{item.id}", params=params, json={})

    def rename(self, item: DriveItem, name: str) -> None:
        self.drive.request("patch", f"{DRIVE_FILES_URL}/{item.id}", params={"fields": "id"}, json={"name": name})

    def _items(self, parent: str, name: str | None = None) -> list[DriveItem]:
        if name is None:
            query = ITEMS_QUERY.format(parent=parent)
        else:
            query = NAMED_QUERY.format(parent=parent, name=_quoted(name))
        params = {"q": query, "fields": ITEM_FIELDS, "pageSize": PAGE_SIZE}
        items: list[DriveItem] = []
        while True:
            page = self.drive.get(DRIVE_FILES_URL, params=params).json()
            items += [DriveItem.from_answer(item) for item in page.get("files", [])]
            if not page.get("nextPageToken"):
                return items
            params["pageToken"] = page["nextPageToken"]


def _quoted(name: str) -> str:
    return name.replace("\\", "\\\\").replace("'", "\\'")
