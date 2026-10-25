"""Reads files from one Google Drive folder with a service account (read-only).

Setup: create a Google Cloud service account with the Drive API enabled, download its JSON key, share the Drive
folder with the service account's e-mail address as Viewer, and put the key's JSON text and the folder ID in the
environment (names in fno/constants.py). Service accounts have no Drive storage of their own, so uploads go through
the owner's own sign-in (GoogleDriveUploadStore), never through this class.
"""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable

import requests

from .drive_session import DriveSession
from .raw_store import RawFileConflict, RawFileStore, ReadOnlyStoreError, path_parts

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_READ_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
FOLDER_TYPE = "application/vnd.google-apps.folder"
CHILD_QUERY = "'{parent}' in parents and name = '{name}' and trashed = false and mimeType {op} '" + FOLDER_TYPE + "'"
ROOT_QUERY = "'{parent}' in parents and trashed = false"
LISTING_QUERY = "'{parent}' in parents and trashed = false and mimeType {op} '" + FOLDER_TYPE + "'"
LISTING_PAGE = 1000  # Drive's largest page
READ_ONLY = "the service account only reads Google Drive: uploads sign in as the owner (GoogleDriveUploadStore)"


def service_account_info(key_text: str) -> dict:
    """The service account key from its JSON text or from that text base64-encoded (one plain line that every
    settings screen keeps intact)."""
    text = key_text.strip()
    if not text.startswith("{"):
        text = base64.b64decode(text).decode("utf-8")
    return json.loads(text)


def service_account_token(key_text: str) -> str:
    """A short-lived access token from a service account key (needs the google-auth package)."""
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    info = service_account_info(key_text)
    credentials = service_account.Credentials.from_service_account_info(info, scopes=[DRIVE_READ_SCOPE])
    credentials.refresh(Request())
    return credentials.token


class GoogleDriveStore(RawFileStore):
    """Files under one shared root folder, in the same tree as the local archive (one folder per path part)."""

    name = "Google Drive"

    def __init__(
        self,
        folder_id: str,
        token: Callable[[], str],
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        """`token` returns a fresh access token (see DriveSession for renewal and retries)."""
        self.folder_id = folder_id
        self.drive = DriveSession(token, session, sleep)
        self._ids: dict[tuple[str, str, bool], str] = {}  # found IDs only (`_child`)

    def _child(self, parent_id: str, name: str, folder: bool) -> str | None:
        """The ID of the named folder or file directly inside a folder; None if absent. A found ID is cached (the
        record is write-once, so a found item stays found); an absence never is: another store instance of the same
        process may create the item next (O9-child: a rehearsal's cache read missed the table its own step had just
        written, 24 Oct), so an absent name is asked of Drive again each time."""
        key = (parent_id, name, folder)
        if key not in self._ids:
            query = CHILD_QUERY.format(
                parent=parent_id, name=name.replace("\\", "\\\\").replace("'", "\\'"), op="=" if folder else "!="
            )
            params = {"q": query, "fields": "files(id, name)", "pageSize": 10}
            response = self.drive.get(DRIVE_FILES_URL, params=params)
            found = response.json().get("files", [])
            if len(found) > 1:
                raise RawFileConflict(f"{len(found)} items named {name!r} in one Drive folder")
            if not found:
                return None
            self._ids[key] = found[0]["id"]
        return self._ids[key]

    def get(self, path: str) -> bytes | None:
        file_id = self._file_id(path, fresh=False)
        return None if file_id is None else self._download(file_id)

    def file_id(self, path: str) -> str | None:
        """The Drive ID of the file at an archive path (None when absent; looked up afresh, never a cached absence)."""
        return self._file_id(path, fresh=True)

    def _file_id(self, path: str, fresh: bool) -> str | None:
        *folders, filename = path_parts(path)
        parent: str | None = self.folder_id
        for name in folders:
            parent = self._child(parent, name, folder=True)
            if parent is None:
                return None
        if fresh:
            self._ids.pop((parent, filename, False), None)
        return self._child(parent, filename, folder=False)

    def checksums(self, folder: str) -> dict[str, str]:
        return self._listing(folder, folders=False)

    def folders(self, folder: str) -> list[str]:
        return sorted(self._listing(folder, folders=True))

    def _listing(self, folder: str, folders: bool) -> dict[str, str]:
        """Name -> MD5 ("" for a folder) of the files, or the folders, directly in a folder; {} if it is absent."""
        parent: str | None = self.folder_id
        for name in path_parts(folder):
            parent = self._child(parent, name, folder=True)
            if parent is None:
                return {}
        found: dict[str, str] = {}
        query = LISTING_QUERY.format(parent=parent, op="=" if folders else "!=")
        params = {"q": query, "fields": "nextPageToken, files(name, md5Checksum)", "pageSize": LISTING_PAGE}
        while True:
            page = self.drive.get(DRIVE_FILES_URL, params=params).json()
            for item in page.get("files", []):
                if item["name"] in found:
                    raise RawFileConflict(f"two items named {item['name']!r} in Drive folder {folder}")
                found[item["name"]] = item.get("md5Checksum", "")
            if not page.get("nextPageToken"):
                return found
            params["pageToken"] = page["nextPageToken"]

    def metadata(self, path: str, fields: str) -> dict | None:
        """The named Drive fields of the file at an archive path (None when absent)."""
        file_id = self.file_id(path)
        if file_id is None:
            return None
        return self.drive.get(f"{DRIVE_FILES_URL}/{file_id}", params={"fields": fields}).json()

    def _download(self, file_id: str) -> bytes:
        return self.drive.get(f"{DRIVE_FILES_URL}/{file_id}", params={"alt": "media"}).content

    def root_listing(self) -> tuple[str, list[str]]:
        """The root folder's name and the names directly inside it (for the access check)."""
        response = self.drive.get(f"{DRIVE_FILES_URL}/{self.folder_id}", params={"fields": "name, mimeType"})
        listing = self.drive.get(
            DRIVE_FILES_URL,
            params={"q": ROOT_QUERY.format(parent=self.folder_id), "fields": "files(name)", "pageSize": 100},
        )
        return response.json()["name"], sorted(f["name"] for f in listing.json().get("files", []))

    def put(self, path: str, data: bytes) -> None:
        raise ReadOnlyStoreError(READ_ONLY)
