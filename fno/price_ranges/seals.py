"""Seals recorded once (part A5; review finding 1): a seal is read once its answer is final and kept as a write-once
seal file in Drive, with its own receipt; readers use the stored seal, and only compute one for a record not yet
sealed.

Story receipts-reach: only a final seal is stored (`SealCheck`). An open one is retried by each run for SCAN_REACH
days; after that, a file still not committed is stored late (any push now would be past its deadline), while a seal
whose evidence could not be read is never stored late: it is reported NOT_RECORDED and readers keep computing it."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime, timedelta

from ..price_distribution.store import DistributionStore
from .folders import live_path, seal_path
from .sealing import UNAVAILABLE, Seal, SealCheck

SCAN_REACH = timedelta(days=7)  # days an open seal is retried: inside `deep_enough`'s 10 days of shallow-clone history
EXPIRED = "late: its receipt was still not committed {days} days after the issue ({why})"
NOT_RECORDED = "{underlying} {day} {issue}: seal NOT recorded, its evidence unreadable for {days} days ({why})"
STORED = "{underlying} {day} {issue}: seal stored ({state})"
PENDING = "{underlying} {day} {issue}: seal pending ({why})"


def _encode(seal: Seal) -> bytes:
    fields = {"sealed_at": seal.sealed_at.isoformat() if seal.sealed_at else None,
              "deadline": seal.deadline.isoformat() if seal.deadline else None, "late": seal.late,
              "reason": seal.reason}  # fmt: skip
    return (json.dumps(fields, sort_keys=True, indent=1) + "\n").encode()


def _decode(data: bytes) -> Seal:
    fields = json.loads(data)

    def moment(text):
        return datetime.fromisoformat(text) if text else None

    return Seal(moment(fields["sealed_at"]), moment(fields["deadline"]), fields["late"], fields["reason"])


class Seals:
    def __init__(self, check: SealCheck, store: DistributionStore, receipt_of: Callable[[str], str],
                 now: Callable[[], datetime], live_path_of: Callable[[str, date, str], str] = live_path,
                 seal_path_of: Callable[[str, date, str], str] = seal_path):  # fmt: skip
        """`receipt_of(drive path)`: the repository path of that file's receipt. `live_path_of` and `seal_path_of`
        (underlying, day, issue): where sealed records and their seals live (default G13b's; G13d gives its own)."""
        self.check, self.store, self.receipt_of, self.now = check, store, receipt_of, now
        self.live_path_of, self.seal_path_of = live_path_of, seal_path_of

    def seal(self, underlying: str, day: date, issue: str) -> Seal:
        stored = self.store.get(self.seal_path_of(underlying, day, issue))
        if stored is not None:
            return _decode(stored)
        return self.check.seal(self.receipt_of(self.live_path_of(underlying, day, issue)), day)

    def record(self, underlying: str, day: date, issue: str) -> str | None:
        """Stores the seal when it is final; returns a line, or None when it was already stored."""
        path = self.seal_path_of(underlying, day, issue)
        if self.store.get(path) is not None:
            return None
        seal = self.check.seal(self.receipt_of(self.live_path_of(underlying, day, issue)), day)
        if seal.waiting is not None:
            names = {"underlying": underlying, "day": day, "issue": issue, "why": seal.reason}
            if self.now().date() - day <= SCAN_REACH:
                return PENDING.format(**names)
            if seal.waiting == UNAVAILABLE:  # a failed read is never a final "late"
                return NOT_RECORDED.format(days=SCAN_REACH.days, **names)
            seal = Seal(None, seal.deadline, True, EXPIRED.format(days=SCAN_REACH.days, why=seal.reason))
        self.store.put(path, _encode(seal))
        state = "late" if seal.late else f"sealed at {seal.sealed_at.isoformat()}"
        return STORED.format(underlying=underlying, day=day, issue=issue, state=state)


def seal_recent(seals: Seals, has_record: Callable[[str, date, str], bool], underlyings, issue: str,
                day: date) -> list[str]:  # fmt: skip
    """Records every final seal of the live issues of the last 8 calendar days before `day` (inside GitHub's log)."""
    lines = []
    for offset in range(1, SCAN_REACH.days + 2):
        past = day - timedelta(days=offset)
        for underlying in underlyings:
            if has_record(underlying, past, issue):
                line = seals.record(underlying, past, issue)
                lines += [line] if line else []
    return lines
