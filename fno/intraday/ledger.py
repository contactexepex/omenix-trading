"""The per-session slot ledger in the repository (story A16): one row per due mark, written once, holding only times,
counts, statuses and SHA-256 values (never a price: raw quotes stay in Drive, design 4.4). A mark nobody took is a
`missed` row, never filled later."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ..models import IST
from .clock import ClockReading
from .document import SnapshotDocument, parse_time, utc_text
from .row_files import read_rows, write_row
from .slots import label
from .status import FAILED, MISSED, SlotVerdict

FIELDS = (
    "session", "mark", "mark_ist", "status", "failures", "request_sent_at", "response_received_at",
    "index_source_time", "lateness_seconds", "index_age_seconds", "expected_contracts", "recorded_contracts",
    "two_sided_contracts", "clock_status", "clock_skew_seconds", "raw_path", "raw_sha256", "source", "first_seen_at",
    "alert", "alert_at", "index_basis",
)  # fmt: skip
NOT_TAKEN = "not_taken"
ROOT = "slots/"  # everything the ledger writes is under this folder
FILE_NAME = ROOT + "{day:%Y}/{day:%m}/{day:%d}/nifty_{day:%Y%m%d}_{mark:%H%M}.csv"
DAY_FOLDER = ROOT + "{day:%Y}/{day:%m}/{day:%d}"
SESSION_FOLDERS = ROOT + "*/*/*"


class SlotLedger:
    """One file per mark (`slots/<YYYY>/<MM>/<DD>/nifty_<YYYYMMDD>_<HHMM>.csv`): two recorder runs in two clones never
    append to the same file."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def path(self, day: date, mark: datetime) -> Path:
        return self.folder / FILE_NAME.format(day=day, mark=mark.astimezone(IST))

    def rows(self, day: date) -> list[dict]:
        return read_rows(self.folder / DAY_FOLDER.format(day=day), "nifty_*.csv")

    def sessions_before(self, day: date) -> list[date]:
        """Sessions before `day` that have ledger rows."""
        found = (date(int(p.parts[-3]), int(p.parts[-2]), int(p.parts[-1])) for p in self.folder.glob(SESSION_FOLDERS))
        return sorted(d for d in found if d < day)

    def append(self, day: date, rows: list[dict]) -> None:
        """Writes each row to its mark's own file; a mark that already has one is refused (rows are written once)."""
        for row in rows:
            write_row(self.path(day, parse_time(row["mark"])), FIELDS, row)


def taken_row(doc: SnapshotDocument, verdict: SlotVerdict, raw_path: str, raw_sha256: str,
              clock: ClockReading | None) -> dict:  # fmt: skip
    """The row of a stored snapshot."""
    received, source_time = doc.index.response_received_at, doc.index_source_time
    return {
        **_mark_fields(doc.session, doc.mark, doc.source), "status": verdict.status,
        "failures": ";".join(verdict.failures), "request_sent_at": utc_text(doc.index.request_sent_at),
        "response_received_at": utc_text(received), "index_source_time": utc_text(source_time),
        "lateness_seconds": _seconds(received, doc.mark), "index_age_seconds": _seconds(received, source_time),
        "expected_contracts": doc.expected_contracts, "recorded_contracts": doc.recorded_contracts,
        "two_sided_contracts": doc.two_sided_contracts, "clock_status": clock.status if clock else "",
        "clock_skew_seconds": _number(clock.worst if clock else None), "raw_path": raw_path, "raw_sha256": raw_sha256,
        "first_seen_at": utc_text(doc.finished_at), "alert": "", "alert_at": "", "index_basis": doc.index_basis,
    }  # fmt: skip


def missed_row(day: date, mark: datetime, source: str, noticed_at: datetime) -> dict:
    """The row of a mark whose window passed with no snapshot stored."""
    row = dict.fromkeys(FIELDS, "")
    row.update(_mark_fields(day, mark, source), status=MISSED, failures=NOT_TAKEN, first_seen_at=utc_text(noticed_at))
    return row


def failed_row(day: date, mark: datetime, source: str, failure: str, noticed_at: datetime) -> dict:
    """The row of a mark whose snapshot could not be taken or stored (nothing is in Drive for it)."""
    row = dict.fromkeys(FIELDS, "")
    row.update(_mark_fields(day, mark, source), status=FAILED, failures=failure, first_seen_at=utc_text(noticed_at))
    return row


def _mark_fields(day: date, mark: datetime, source: str) -> dict:
    return {"session": day.isoformat(), "mark": utc_text(mark), "mark_ist": label(mark), "source": source}


def _seconds(later: datetime | None, earlier: datetime | None) -> str:
    return _number((later - earlier).total_seconds()) if later and earlier else ""


def _number(value: float | None) -> str:
    return "" if value is None else f"{value:.1f}"
