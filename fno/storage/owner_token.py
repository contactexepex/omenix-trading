"""The owner's Google sign-in for Drive uploads: swaps the refresh token from the one-time consent
(tools/gdrive_oauth_setup.py) for a short-lived access token. A refusal (expired or revoked consent) is raised as
DriveSignInRefused, naming Google's error code only, never a credential."""

from __future__ import annotations

import requests

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
TOKEN_TIMEOUT_SECONDS = 30
REFUSED_STATUSES = frozenset({400, 401, 403})  # Google's answers to an expired, revoked or unknown key
UNKNOWN_REASON = "no error code"


class DriveSignInRefused(RuntimeError):
    """Google refused the owner's Drive sign-in (most often `invalid_grant`: the consent expired or was revoked)."""

    def __init__(self, reason: str):
        super().__init__(f"Google refused the Drive upload sign-in: {reason}")
        self.reason = reason


class OwnerAccessToken:
    """A callable returning a fresh access token each time it is called (DriveSession calls it again on a 401)."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str, session: requests.Session | None = None):
        self._form = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        self._session = session or requests.Session()

    def __call__(self) -> str:
        response = self._session.post(GOOGLE_TOKEN_URL, data=self._form, timeout=TOKEN_TIMEOUT_SECONDS)
        if response.status_code in REFUSED_STATUSES:
            raise DriveSignInRefused(_error_code(response))
        response.raise_for_status()
        return response.json()["access_token"]


def _error_code(response: requests.Response) -> str:
    try:
        code = response.json().get("error")
    except ValueError:
        code = None
    return code if isinstance(code, str) and code.isidentifier() else UNKNOWN_REASON
