"""`python -m fno drive-check`: proves the Google Drive project folder can be read, without printing any secret."""

from __future__ import annotations

import os

import requests

from ..constants import ENV_GDRIVE_FOLDER_ID, ENV_GDRIVE_SERVICE_ACCOUNT_JSON
from .google_drive import GoogleDriveStore, service_account_info, service_account_token

HINTS = {
    403: "the Google Drive API may not be enabled in the key's Cloud project",
    404: "the folder is not shared with the service account (Viewer), or the folder ID is wrong",
}


def drive_check_lines(env=os.environ, token_for=service_account_token, session=None) -> list[str]:
    key, folder = env.get(ENV_GDRIVE_SERVICE_ACCOUNT_JSON), env.get(ENV_GDRIVE_FOLDER_ID)
    missing = [
        name for name, value in ((ENV_GDRIVE_SERVICE_ACCOUNT_JSON, key), (ENV_GDRIVE_FOLDER_ID, folder)) if not value
    ]
    if missing:
        return [f"not set: {', '.join(missing)}"]
    try:
        info = service_account_info(key)
    except ValueError as exc:
        return [f"{ENV_GDRIVE_SERVICE_ACCOUNT_JSON} is not a readable key (JSON or base64 of it): {type(exc).__name__}"]
    lines = [f"key read: type {info.get('type')}, Cloud project {info.get('project_id')}"]
    try:
        store = GoogleDriveStore(folder, lambda: token_for(key), session)
    except Exception as exc:  # noqa: BLE001 - report any sign-in failure plainly
        return [*lines, f"sign-in FAILED: {type(exc).__name__}: {exc}"]
    lines.append("signed in to Google (token obtained)")
    try:
        name, children = store.root_listing()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        return [*lines, f"project folder FAILED: HTTP {status}; {HINTS.get(status, str(exc))}"]
    lines.append(f"project folder visible: '{name}'")
    lines.append(f"inside it: {', '.join(children) if children else 'nothing yet (expected before the first upload)'}")
    return lines
