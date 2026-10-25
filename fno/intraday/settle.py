"""Brings a session's ledger up to date (story A16): a row for the snapshot just taken, a row for a due mark whose copy
is in Drive with no row yet (a run that stopped after saving; the copy is chosen by `SnapshotFiles`' fixed rule), and
a `missed` row for every due mark with no copy. Then the streak alert, at most one send per settlement: its outcome
line is kept in the newest row."""

from __future__ import annotations

import hashlib
from datetime import date, datetime

from ..alerts.sender import AlertSender
from .document import SnapshotDocument, utc_text
from .ledger import SlotLedger, failed_row, missed_row, taken_row
from .slots import marks, window_end
from .snapshot_files import SnapshotFiles
from .status import verdict
from .streak import streak_alert_text

ALERT_LINE = "ALERT: {text} -> {outcome}"


class Settlement:
    def __init__(self, files: SnapshotFiles, ledger: SlotLedger, alerts: AlertSender):
        self.files, self.ledger, self.alerts = files, ledger, alerts
        self.source = files.source

    def settle(self, day: date, now: datetime, taken=None, failed=None) -> tuple[list[dict], str]:
        """The rows written now, and the alert line ("" when none was due). `taken`: (document, bytes, clock reading,
        path) of the snapshot just taken; `failed`: (mark, failure name) of a mark whose snapshot failed."""
        existing = self.ledger.rows(day)
        have = {row["mark"] for row in existing}
        new = []
        for mark in marks(day):
            if utc_text(mark) in have:
                continue
            if taken is not None and taken[0].mark == mark:
                new.append(self._row(day, mark, *taken, new))
            elif failed is not None and failed[0] == mark:
                new.append(failed_row(day, mark, self.source, failed[1], now))
            elif window_end(mark) < now:
                path = self.files.unrowed_copy(day, mark)
                data = self.files.read(path)
                document = SnapshotDocument.from_bytes(data) if data else None
                new.append(self._row(day, mark, document, data, None, path, new) if document else missed_row(
                    day, mark, self.source, now))  # fmt: skip
        line = next((line for position in range(len(new)) if (line := self._alert(existing + new[: position + 1],
                                                                                  now))), "")  # fmt: skip
        self.ledger.append(day, new)
        return new, line

    def _row(self, day: date, mark: datetime, document: SnapshotDocument, data: bytes, reading, path: str,
             new: list[dict] | None = None) -> dict:  # fmt: skip
        judged = verdict(document, self._previous_level(day, mark, new or []))
        return taken_row(document, judged, path, hashlib.sha256(data).hexdigest(), reading)

    def _previous_level(self, day: date, mark: datetime, new: list[dict]) -> float | None:
        """The previous mark's level, read from the copy its row names (a row written earlier in this settlement
        counts too); for the `index_repeated` flag only."""
        session_marks = marks(day)
        position = session_marks.index(mark)
        if position == 0:
            return None
        previous = utc_text(session_marks[position - 1])
        row = next((r for r in new if r["mark"] == previous), None)
        path = (row["raw_path"] or None) if row else self.files.used(day, session_marks[position - 1])
        data = self.files.read(path)
        return SnapshotDocument.from_bytes(data).index_level if data else None

    def _alert(self, rows: list[dict], now: datetime) -> str:
        """The streak alert due as of the newest row, kept in that row with its time (rows are settled in mark
        order, so a streak followed by a good mark in the same settlement is still alerted)."""
        text = streak_alert_text(rows, now)
        if not text:
            return ""
        rows[-1].update(alert=ALERT_LINE.format(text=text, outcome=self.alerts.send(text)), alert_at=utc_text(now))
        return rows[-1]["alert"]
