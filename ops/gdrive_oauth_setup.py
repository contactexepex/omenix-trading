"""One-time setup, run by the owner on their own computer: lets the cloud upload to the owner's Google Drive as the
owner (service accounts cannot: they have no storage quota).

    pip install google-auth-oauthlib
    python3 gdrive_oauth_setup.py client_secret_<...>.json     (from any folder; it needs nothing else)

A browser opens; sign in with the Google account that owns the fno-research folder and allow access. The script
prints three values to THIS terminal only. Copy each into the cloud environment's settings under the printed name.
Never paste them into a chat, an issue or a file. The downloaded client JSON can be deleted afterwards.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Standalone on purpose (the owner runs it from any folder, like tools/nse_raw_download): these must equal the names in
# fno/constants.py, which tests/test_gdrive_oauth_setup.py checks.
DRIVE_FULL_SCOPE = "https://www.googleapis.com/auth/drive"
ENV_GDRIVE_OAUTH_CLIENT_ID = "FNO_GDRIVE_OAUTH_CLIENT_ID"
ENV_GDRIVE_OAUTH_CLIENT_SECRET = "FNO_GDRIVE_OAUTH_CLIENT_SECRET"
ENV_GDRIVE_OAUTH_REFRESH_TOKEN = "FNO_GDRIVE_OAUTH_REFRESH_TOKEN"

USAGE = "usage: python3 gdrive_oauth_setup.py <downloaded client_secret JSON>"


def settings_lines(client_id: str, client_secret: str, refresh_token: str) -> list[str]:
    """The three environment settings, one per line, ready to copy."""
    return [
        "Add these three values in the cloud environment's settings (names exactly as shown):",
        f"{ENV_GDRIVE_OAUTH_CLIENT_ID}={client_id}",
        f"{ENV_GDRIVE_OAUTH_CLIENT_SECRET}={client_secret}",
        f"{ENV_GDRIVE_OAUTH_REFRESH_TOKEN}={refresh_token}",
        "Do not paste them into a chat or a file. Then tell the orchestrator: 'Drive upload keys added'.",
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not Path(argv[0]).is_file():
        print(USAGE)
        return 2
    from google_auth_oauthlib.flow import InstalledAppFlow

    client = json.loads(Path(argv[0]).read_text())["installed"]
    flow = InstalledAppFlow.from_client_secrets_file(argv[0], scopes=[DRIVE_FULL_SCOPE])
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not credentials.refresh_token:
        print(
            "Google returned no refresh token. Remove the app's access at myaccount.google.com/permissions and rerun."
        )
        return 1
    print("\n".join(settings_lines(client["client_id"], client["client_secret"], credentials.refresh_token)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
