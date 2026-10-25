"""`python -m fno quotes record-indices` (story A4c): the traded index options after NIFTY's push; one result line per
index, one #fno-desk alert naming every index not recorded, exit 1 if any. Never places orders."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping

from ..alerts.output import announce
from ..alerts.sender import AlertSender
from ..models import now_ist
from ..research_data.calendar import CalendarError
from .indices import ATTEMPTED, CLOSED_NONE, QUIET_STATUSES, IndexRecording, closes_none
from .recorder import QuoteSnapshotRecorder, RecordResult

INDEX_LINE = "{underlying} {status}: {snapshot_id} ({rows} contracts, complete={complete}){outcome}"
INDEX_ALERT = "3 pm index recorder: not recorded today: {names}. Data only; NIFTY is separate{pointer}."
# A4c-2 (judge 571 should-fix 2): only an attempt writes a sidecar, so only the attempted indices are pointed to it
SIDECAR_POINTER = "; the sidecars in research/data/quotes/groww/ say why for {names}"
INDEX_CALENDAR_STOP = "3 pm index recorder stopped, nothing recorded: {error} ({file})"


def record_indices(build: Callable[[], Mapping[str, QuoteSnapshotRecorder]], alerts: AlertSender, calendar_file: str,
                   now=now_ist, sleep=time.sleep) -> int:  # fmt: skip
    try:
        results = IndexRecording(build(), now, sleep).run()
    except CalendarError as error:
        message = INDEX_CALENDAR_STOP.format(error=error, file=calendar_file)
        print(message)
        announce(alerts, message)
        return 1
    for underlying, result in results.items():
        print(_line(underlying, result))
    missing = {name: result for name, result in results.items() if _missing(result)}
    if missing:
        announce(alerts, index_alert(missing))
    return 1 if missing else 0


def index_alert(missing: Mapping[str, RecordResult]) -> str:
    """The one alert: each index not recorded with its outcome, and the sidecar pointer for the attempted ones only."""
    names = "; ".join(f"{name} ({outcome(result)})" for name, result in missing.items())
    attempted = [name for name, result in missing.items() if result.status == ATTEMPTED]
    pointer = SIDECAR_POINTER.format(names=", ".join(attempted)) if attempted else ""
    return INDEX_ALERT.format(names=names, pointer=pointer)


def outcome(result: RecordResult) -> str:
    """The index's own outcome (A4c-2), the one text its result line and the alert both print, so they cannot
    disagree: empty for a complete recording; "canonical none" exactly when its day was closed none."""
    texts = [text for text in (result.reason, result.raw_file_error) if text]
    if _missing(result) and not texts:
        texts.append("incomplete" if result.status == ATTEMPTED else result.status)
    if closes_none(result):
        texts.append(CLOSED_NONE)
    return ", ".join(texts)


def _missing(result: RecordResult) -> bool:
    return not result.complete and result.status not in QUIET_STATUSES


def _line(underlying: str, result: RecordResult) -> str:
    text = outcome(result)
    return INDEX_LINE.format(underlying=underlying, status=result.status, snapshot_id=result.snapshot_id or "-",
                             rows=result.rows, complete=result.complete,
                             outcome=f" - {text}" if text else "")  # fmt: skip
