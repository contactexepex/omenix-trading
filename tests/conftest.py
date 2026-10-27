"""Shared test fixtures and offline fakes for the data-ingestion suite (refactor stage 3).

Absolute safety rule (CLAUDE.md, and this task's brief): a test must NEVER make a live network call or reach
Slack, Drive, Groww or NSE. Every test here injects a fake HTTP session or a fake client and writes only to
``tmp_path``. To keep that true even if a test accidentally reached for real credentials, this module blanks every
secret environment variable at import time (before collection) and again before each test, so a real Slack/Drive/
Groww client would fail fast with "no credentials" rather than connect. ``pytest never calls Groww live`` is a repo
rule.

The ``data`` marker (see ``pytest.ini``) marks tests that read data from the "verified cache". They build a TEMP
cache from tiny committed fixtures under a ``tmp_path`` (never Google Drive): a ``LocalFolderStore`` stands in for
Drive and the ``DriveCache`` verifies every byte against its receipt, exactly as production does offline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# Every environment variable that could carry a real credential or endpoint in this container. Blanked so no test can
# reach a live service, and so any accidental client build fails fast instead of connecting.
SENSITIVE_ENV = (
    "FNO_SLACK_BOT_TOKEN", "FNO_SLACK_CHANNEL_ID",
    "FNO_GDRIVE_SERVICE_ACCOUNT_JSON", "FNO_GDRIVE_FOLDER_ID",
    "FNO_GDRIVE_OAUTH_CLIENT_ID", "FNO_GDRIVE_OAUTH_CLIENT_SECRET", "FNO_GDRIVE_OAUTH_REFRESH_TOKEN",
    "FNO_DB_URL",
    "GROWW_ACCESS_TOKEN", "GROWW_API_KEY", "GROWW_API_SECRET", "GROWW_TOTP_SECRET",
    "MOTHERDUCK_TOKEN", "MOTHERDUCK_READ_TOKEN", "MOTHERDUCK_INBOX_TOKEN",
    "SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET", "SLACK_WEBHOOK_URL",
)  # fmt: skip

for _name in SENSITIVE_ENV:  # blank before collection, so import-time code never sees a real secret
    os.environ.pop(_name, None)


@pytest.fixture(autouse=True)
def _blank_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every secret unset for the duration of each test (defence in depth over the import-time scrub)."""
    for name in SENSITIVE_ENV:
        monkeypatch.delenv(name, raising=False)


# --------------------------------------------------------------------------- fake HTTP (NSE archive sources)


@dataclass
class FakeResponse:
    """A stand-in for ``requests.Response`` carrying exactly what the code under test reads."""

    status_code: int = 200
    content: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    _json: object = None

    def json(self) -> object:
        if self._json is None:
            raise ValueError("no JSON body")
        return self._json


@dataclass
class FakeHttpSession:
    """A ``requests.Session`` stand-in for NSE archive sources: answers each URL from ``routes`` (a single
    ``FakeResponse`` answers every URL), and records every URL asked for. Never touches the network."""

    routes: object = None  # FakeResponse, or dict[url -> FakeResponse]
    requested: list[str] = field(default_factory=list)
    method_calls: list[str] = field(default_factory=list)

    def _answer(self, url: str) -> FakeResponse:
        self.requested.append(url)
        if isinstance(self.routes, dict):
            return self.routes.get(url, FakeResponse(status_code=404))
        return self.routes if self.routes is not None else FakeResponse(status_code=404)

    def get(self, url: str, timeout: float | None = None) -> FakeResponse:
        self.method_calls.append("GET")
        return self._answer(url)

    def head(self, url: str, timeout: float | None = None) -> FakeResponse:
        self.method_calls.append("HEAD")
        return self._answer(url)


@pytest.fixture
def http_fakes() -> SimpleNamespace:
    """The HTTP fakes, handed to tests as a fixture so no test imports ``conftest`` directly."""
    return SimpleNamespace(Response=FakeResponse, Session=FakeHttpSession)


@pytest.fixture(autouse=True)
def _forget_the_shared_pacer():
    """`main` attaches the process-wide pacer to the pause log; no test may leave it pointing at the repository's files
    or carrying a host's state to the next test (story R1b2)."""
    from fno.shared.http_pacing import SHARED_PACER

    yield
    SHARED_PACER.attach(None, None, False)
    SHARED_PACER._hosts.clear()
