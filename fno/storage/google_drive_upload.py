"""Saves files into the owner's Google Drive project folder, signed in as the owner (a service account cannot: it has
no storage quota). Keeps the archive rules: the same bytes again change nothing, different bytes at an existing path
raise RawFileConflict, and folders are created as needed.

Every new folder and file is created under an ID asked from Drive beforehand, so a create that is retried after a
dropped connection can never make a second copy: Drive answers 409 "fileIdInUse" to the repeat. Meant for one writer
at a time (the librarian or the library); the folder and file lookups are re-checked before anything is created.
"""

from __future__ import annotations

import hashlib
import json

from .google_drive import DRIVE_FILES_URL, FOLDER_TYPE, GoogleDriveStore
from .raw_store import RawFileConflict, StoredCopyDamaged, path_parts

DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
GENERATE_IDS_URL = f"{DRIVE_FILES_URL}/generateIds"
IDS_PER_REQUEST = 100
ID_IN_USE = 409  # Drive's answer when an item with that ID already exists: our earlier attempt got through
FILE_TYPE = "application/octet-stream"  # raw files keep their bytes exactly; Drive never converts them


class GoogleDriveUploadStore(GoogleDriveStore):
    name = "Google Drive (owner upload)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._new_ids: list[str] = []  # IDs Drive reserved for us, used one per new folder or file

    def put(self, path: str, data: bytes) -> None:
        *folders, filename = path_parts(path)
        parent = self.folder_id
        for name in folders:
            parent = self._child(parent, name, folder=True) or self._create_folder(parent, name)
        existing = self._fresh_child(parent, filename, folder=False)
        if existing is not None:
            if self._download(existing) != data:
                raise RawFileConflict(f"{path} already exists in Drive with different content")
            return
        self._ids[(parent, filename, False)] = self._create_file(parent, filename, data)

    def _fresh_child(self, parent_id: str, name: str, folder: bool) -> str | None:
        """Looks again instead of trusting a cached "absent" (something may have been created since)."""
        self._ids.pop((parent_id, name, folder), None)
        return self._child(parent_id, name, folder)

    def _create_folder(self, parent_id: str, name: str) -> str:
        existing = self._fresh_child(parent_id, name, folder=True)
        if existing is not None:
            return existing
        folder_id = self._new_id()
        metadata = {"id": folder_id, "name": name, "mimeType": FOLDER_TYPE, "parents": [parent_id]}
        self.drive.post(DRIVE_FILES_URL, json=metadata, params={"fields": "id"}, accept=frozenset({ID_IN_USE}))
        self._ids[(parent_id, name, True)] = folder_id
        return folder_id

    def _create_file(self, parent_id: str, name: str, data: bytes) -> str:
        file_id = self._new_id()
        metadata = {"id": file_id, "name": name, "parents": [parent_id], "mimeType": FILE_TYPE}
        parts = {"metadata": ("metadata", json.dumps(metadata), "application/json"), "file": (name, data, FILE_TYPE)}
        params = {"uploadType": "multipart", "fields": "id, md5Checksum"}
        response = self.drive.post(DRIVE_UPLOAD_URL, files=parts, params=params, accept=frozenset({ID_IN_USE}))
        checksum = response.json().get("md5Checksum") if response.status_code != ID_IN_USE else None
        if not self._holds(file_id, data, checksum):
            raise StoredCopyDamaged(f"{name}: Drive holds different bytes than were sent (Drive ID {file_id})")
        return file_id

    def _holds(self, file_id: str, data: bytes, checksum: str | None) -> bool:
        """Whether Drive's copy equals the bytes sent: by Drive's MD5 of what it received, or, for the repeat of a
        create that got through (Drive then sends no checksum), by reading the file back."""
        if checksum is None:
            return self._download(file_id) == data
        return checksum == hashlib.md5(data).hexdigest()  # noqa: S324 - Drive's own transfer checksum, not security

    def replace_contents(self, file_id: str, data: bytes) -> None:
        """New contents for an existing file, checked against Drive's MD5. Only for index files (IndexFileStore):
        raw files are never replaced."""
        params = {"uploadType": "media", "fields": "md5Checksum"}
        headers = {"Content-Type": FILE_TYPE}
        response = self.drive.request(
            "patch", f"{DRIVE_UPLOAD_URL}/{file_id}", params=params, data=data, headers=headers
        )
        if response.json().get("md5Checksum") != hashlib.md5(data).hexdigest():  # noqa: S324 - Drive's checksum
            raise StoredCopyDamaged(f"Drive file {file_id} holds different bytes than were sent")

    def _new_id(self) -> str:
        if not self._new_ids:
            params = {"count": IDS_PER_REQUEST, "space": "drive", "type": "files"}
            self._new_ids = list(self.drive.get(GENERATE_IDS_URL, params=params).json()["ids"])
        return self._new_ids.pop()
