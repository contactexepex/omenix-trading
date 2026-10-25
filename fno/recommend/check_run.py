"""The evening check run (story REC1c): every recorded day of the last 60 sessions whose latest check is not final is
checked again, each into its own write-once file `<day>.check.<check day>.json` with its receipt pushed; a day that
becomes final (complete, or incomplete because a source was unavailable) gets one #fno-desk line. A day that cannot
be read is alerted and fails the step, never the other days; the evening edition was already posted before it."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..alerts.sender import AlertSender
from ..school.contracts.seal import StaleSeal
from .check import OutcomeLookup, check, unreadable
from .check_record import FINAL, CheckRecord
from .check_text import answer_text, trades_text
from .codec import decode
from .constants import WINDOW_SESSIONS
from .contracts import RecordRefused
from .ports import DataDisagrees, InputFailed
from .run import DayResult
from .shelf import ReceiptShelf, check_path
from .store import record_path
from .write_once import NotOurs, NotSaved, WriteOnce

RECEIPT_MESSAGE = "Receipt: the recommender's check of {day} on {on}"
NOT_CHECKED = "recommender check NOT made for {day}: {why}"
NOTHING = "recommender check {on}: no recorded day waits for a check"
LINE = "PAPER ONLY. Recommender check for {day:%d %b %Y}: {verdict}. {answer} {trades} Record {path}, SHA-256 {short}."


@dataclass(frozen=True)
class CheckPorts:
    receipts: Path  # the repository's receipts folder of the data area (`receipts/data`)
    read: Callable[[str], bytes]  # a data-area file, verified against its receipt
    sessions: Callable[[date, date], list[date]]  # NSE sessions from a to b, both included
    lookup: Callable[[], OutcomeLookup]  # a fresh lookup per run (its cache is per run)


class CheckRun:
    def __init__(self, ports: CheckPorts, keeper: WriteOnce, alerts: AlertSender, clock: Callable[[], datetime]):
        self.ports, self.keeper, self.alerts, self.clock = ports, keeper, alerts, clock
        self.shelf = ReceiptShelf(ports.receipts)

    def run(self, on: date) -> DayResult:
        lookup, lines, ok = self.ports.lookup(), [], True
        for day in self.shelf.recorded_days(on):  # however old (judge 658.1 S1)
            last = len(self.ports.sessions(day, on)) >= WINDOW_SESSIONS
            try:  # each day on its own: one unreadable file never stops the others (self-review, blocking)
                if not self._final(day, on):
                    lines += self._check(day, on, lookup, last)
            except DataDisagrees as disagree:  # read and contradictory: final at once (judge 658.1 m1)
                lines += self._failed(day, on, True, str(disagree))
                ok = False
            except (InputFailed, NotSaved, RecordRefused) as failed:  # RecordRefused covers a damaged check file
                lines += self._failed(day, on, last, str(failed))
                ok = False
        return DayResult(tuple(lines) or (NOTHING.format(on=on),), ok)

    def _check(self, day: date, on: date, lookup: OutcomeLookup, last: bool) -> list[str]:
        data = self._read(record_path(day))
        record = decode(data)
        result = check(record, hashlib.sha256(data).hexdigest(), on, self.clock(), lookup, last)
        kept, stands = self._keep(result)
        if stands.verdict not in FINAL:
            return [f"recommender check {day}: {stands.verdict.value}, {stands.open_positions} position(s) still open"]
        line = _line(record, stands, kept)
        return [self.alerts.send(line), line]

    def _failed(self, day: date, on: date, last: bool, why: str) -> list[str]:
        """A failed check is alerted; a read error is tried again next evening, and at the last check, or for records
        that disagree, it is written final as well."""
        line = NOT_CHECKED.format(day=day, why=why)
        lines = [self.alerts.send(line), line]
        if last:
            try:
                self._keep(unreadable(day, on, self.clock(), why))
            except NotSaved as unsaved:
                lines += [self.alerts.send(NOT_CHECKED.format(day=day, why=unsaved))]
        return lines

    def _keep(self, result: CheckRecord):
        day, on = result.session, result.checked_on
        kept = self.keeper.keep(check_path(day, on), result.to_bytes(), _vouch(day, on),
                                RECEIPT_MESSAGE.format(day=day, on=on))  # fmt: skip
        return kept, parse_check(kept.payload)

    def _final(self, day: date, on: date) -> bool:
        """Only checks made on or before `on` count (judge 660 m1): a catch-up for a past day sees what existed then."""
        checks = self.shelf.checks(day, on)
        return bool(checks) and parse_check(self._read(check_path(day, checks[-1]))).verdict in FINAL

    def _read(self, path: str) -> bytes:
        """A data-area file verified against its receipt; any failure to read it is an input failure of that day."""
        try:
            return self.ports.read(path)
        except (StaleSeal, OSError, ValueError, KeyError) as unreadable:
            raise InputFailed(f"{path}: {type(unreadable).__name__}") from None


def parse_check(data: bytes) -> CheckRecord:
    try:
        return CheckRecord.from_bytes(data)
    except RecordRefused:
        raise
    except (ValueError, KeyError, TypeError) as damaged:  # a damaged check file: that day's problem, never the run's
        raise RecordRefused(f"a check file does not read ({type(damaged).__name__})") from None


def _vouch(day: date, on: date):
    def vouch(held: bytes) -> None:
        try:
            stored = parse_check(held)
        except RecordRefused as refused:
            raise NotOurs(str(refused)) from None
        if (stored.session, stored.checked_on) != (day, on):
            raise NotOurs(f"a check of {stored.session} on {stored.checked_on}")

    return vouch


def _line(record, stands: CheckRecord, kept) -> str:
    return LINE.format(day=record.session, verdict=stands.verdict.value.replace("_", " "),
                       answer=answer_text(record, stands), trades=trades_text(stands), path=kept.path,
                       short=kept.sha256[:12])  # fmt: skip
