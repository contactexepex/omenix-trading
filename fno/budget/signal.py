"""The month's budget signal (story BG1): the cap level as data a later routine acts on, written to
`accounting/budget/<YYYY-MM>_signal.json`, and the alert line, sent through `AlertSender`. This story wires only a
dry-run sender: nothing is posted to Slack until a later routine wires the Slack sender."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..alerts.sender import AlertSender
from .cap import CapReading, shown_pct
from .constants import AI_ROLE_STOP_ORDER, BUDGET_ALERT, BUDGET_NO_CAP, BUDGET_STOP, BUDGET_UNKNOWN

SIGNAL_FOLDER = "accounting/budget"
CODE_JOBS = "keep running"
NO_MEASURE = "no alert: the level is unknown (no measured minutes to compare with)"
NO_CAP_ALERT = "no alert: no AI cap (owner, 24 Oct 2026)"  # BG1-u
ALERT_TEXT = (
    "Omenix F&O SYSTEM: AI budget {month}: books and roles used {pct:.1f}% of their cap ({used:,.2f} of {cap:,.2f} "
    "minutes); at 100% AI roles stop ({order}); code jobs keep running"
)
STOP_TEXT = (
    "Omenix F&O SYSTEM: AI budget {month}: cap reached ({pct:.1f}%, {used:,.2f} of {cap:,.2f} minutes): AI roles stop "
    "in this order: {order}; code jobs keep running"
)


def signal_path(month: str) -> str:
    return f"{SIGNAL_FOLDER}/{month}_signal.json"


def alert_text(month: str, reading: CapReading) -> str:
    """The line to send at `alert` or `stop`, else empty."""
    template = {BUDGET_ALERT: ALERT_TEXT, BUDGET_STOP: STOP_TEXT}.get(reading.level)
    if template is None:
        return ""
    order = ", then ".join(AI_ROLE_STOP_ORDER)
    return template.format(month=month, pct=shown_pct(reading.pct_of_cap), used=reading.books_and_roles_minutes,
                           cap=reading.cap_minutes, order=order)  # fmt: skip


def signal_data(month: str, reading: CapReading, missing_captures: int, computed_at: datetime) -> dict:
    return {
        "month": month,
        "level": reading.level,
        "pct_of_cap": None if reading.pct_of_cap is None else round(reading.pct_of_cap, 2),
        "books_and_roles_minutes": reading.books_and_roles_minutes,
        "cap_minutes": reading.cap_minutes,
        "basis": reading.basis,
        "missing_captures": missing_captures,
        "note": reading.note,
        "alert_text": alert_text(month, reading),
        "stop_ai_roles": reading.level == BUDGET_STOP,
        "stop_order": list(AI_ROLE_STOP_ORDER),
        "code_jobs": CODE_JOBS,
        "computed_at": computed_at.isoformat(),
    }


def write_signal(root: Path, data: dict) -> Path:
    path = root / signal_path(data["month"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path


def send_alert(sender: AlertSender, data: dict) -> str:
    if data["alert_text"]:
        return sender.send(data["alert_text"])
    quiet = {BUDGET_UNKNOWN: NO_MEASURE, BUDGET_NO_CAP: NO_CAP_ALERT}
    return quiet.get(data["level"], "no alert: below the alert level")
