"""Composition root of story O5's public-record scan, standard library only (story DR1 audit item 6): the commit hook
runs the scan on every commit, also in a routine whose packages are still installing; importing the whole app made the
AI books' sealed answers wait for pip and miss 15:15 (22 and 23 Oct). The #fno-desk sender (`fno.alerts.sender`, which
needs `requests`) is built only when a refusal is alerted, never on import, so the scan never pulls `requests` in."""

from __future__ import annotations

import os

from .catalogue import ALLOWED_VALUES, credential_patterns, record_patterns
from .forbidden_files import MOVED_VIX_FILES, PAPER_ACCOUNT_FILES, RAW_GROWW_QUOTES
from .scanner import RecordScanner

NO_SENDER = "alert NOT sent: the #fno-desk sender could not be loaded ({kind}: {why}) | {text}"


def build_record_scanner() -> RecordScanner:
    """The public-record scan (story O5): every pattern of the catalogue for records, credential shapes for code, with
    the #fno-desk channel ID allowed; raw Groww quote files (story A4b), private paper accounts (E2d) and data moved to
    Drive (O9b) are refused by path."""
    forbidden = (RAW_GROWW_QUOTES, PAPER_ACCOUNT_FILES, MOVED_VIX_FILES)
    return RecordScanner(record_patterns(), ALLOWED_VALUES, credential_patterns(), forbidden)


def send_alert(text: str, alerts=None) -> str:
    """The sender's outcome; when the sender cannot even be loaded or built (a package missing or half installed), the
    line says so with the text, so the routine can post it: the refusal itself never depends on it. A Rust extension's
    panic (pyo3's PanicException, a BaseException) is not caught: the hook then exits non-zero, so the commit is still
    refused, only without the text."""
    if alerts is None:
        try:
            alerts = _build_alert_sender()
        except Exception as failure:  # noqa: BLE001 - a missing or half-installed package (judge 549): print the text
            return NO_SENDER.format(kind=type(failure).__name__, why=_why(failure), text=text)
    return alerts.send(text)


def _build_alert_sender():
    """#fno-desk through `FNO_SLACK_BOT_TOKEN` (else a no-op sender); imported lazily so the scan's root stays
    standard-library only (no `requests`) until a refusal is actually alerted."""
    from ..alerts.sender import NoAlertSender, SlackChannelAlerts
    from ..constants import ENV_FNO_SLACK_BOT_TOKEN, FNO_DESK_CHANNEL_ID

    token = os.environ.get(ENV_FNO_SLACK_BOT_TOKEN)
    return SlackChannelAlerts(token, FNO_DESK_CHANNEL_ID) if token else NoAlertSender()


def _why(failure: Exception) -> str:
    """The missing module's name for an ImportError; else only the error's class (its message may hold a path)."""
    return getattr(failure, "name", None) or "load failed"
