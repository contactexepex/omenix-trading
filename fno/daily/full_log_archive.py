"""Story O1-status-only, design item 6: at the run's end, its private full log is written once to Drive through O9's
data store (one file per run attempt, its SHA-256 receipt committed). It is a debugging copy, not the day's record: if
Drive is down, one alert says so and the day's status, line and exit code stay as they are (judge 443 note)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ..alerts.sender import AlertSender
from ..desk.daily_ports import Committer
from ..storage.data_store import DataStore
from .full_log import FullRunLog

FULL_LOG_FILE = "daily_runs/full/{day}/{run_id}.json"  # in Drive's data area; never in the repository
NOT_SAVED = "F&O daily run {day}: full run log NOT saved to Drive ({kind}); the day's record is unchanged"
RECEIPT_MESSAGE = "Receipt: daily run full log {day}"


class DriveNotSet(RuntimeError):
    """The four owner Drive settings are not all set: there is nowhere to keep the copy."""


class FullLogArchive:
    def __init__(self, full: FullRunLog, store: Callable[[], DataStore], committer: Committer, alerts: AlertSender):
        self.full, self.store, self.committer, self.alerts = full, store, committer, alerts

    def archive(self, day: date) -> None:
        """Only the error's type is alerted: a Drive error's text can name a private folder (A4b)."""
        path = self.full.path(day)
        if not path.is_file():
            return
        try:
            store = self.store()
            receipt = store.put(FULL_LOG_FILE.format(day=day, run_id=store.run_id), path.read_bytes())
            self.committer.commit([store.receipts.file_for(receipt.path)], RECEIPT_MESSAGE.format(day=day))
        except Exception as failure:  # noqa: BLE001 - a debugging copy never changes the day's outcome
            self.alerts.send(NOT_SAVED.format(day=day, kind=type(failure).__name__))
