"""The card's status (story T1 v1): always `NO TRADE`, with the reason read from the committed playbook registry and
the books' paper accounts. Card v1 has no trade fields, so even a version at `paper` gives `NO TRADE`
(`trade_fields_not_built`), and the owner is pointed to the desk's own records: a card never invents a trade."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date

from ..constants import (
    BOOKS,
    CARD_DATA_CHECK_FAILED,
    CARD_NO_APPROVED_STRATEGY,
    CARD_TRADE_FIELDS_NOT_BUILT,
    JOURNAL_FOLDER,
    PLAYBOOK_FOLDER,
    PLAYBOOK_REGISTRY_FILE,
    CardStatus,
    PlaybookStatus,
)
from ..desk.trade_counts import version_tag
from ..playbook.fields import PlaybookError
from ..playbook.registry import parse_rows
from .committed import CommittedRecords
from .sections import CardSection, StatusReading, StatusSource, UsedRecord

REGISTRY_PATH = f"{PLAYBOOK_FOLDER}/{PLAYBOOK_REGISTRY_FILE}"
POSITIONS_PATH = JOURNAL_FOLDER + "/{book}/account/positions.json"
REASONS = {
    CARD_NO_APPROVED_STRATEGY: "no strategy has passed: no playbook version is approved to paper",
    CARD_TRADE_FIELDS_NOT_BUILT: (
        "{count} version(s) at paper ({names}), but card v1 cannot show trade fields (T1 slice B): "
        "see the desk's decision records"
    ),
    CARD_DATA_CHECK_FAILED: "the playbook registry or a paper account could not be read, so no status can be trusted",
}
TRADES_LINE = "Paper trades so far: {total} ({books})"
NOT_READ = "{path}: not readable ({why})"


class RegistryStatus(StatusSource):
    def __init__(self, records: CommittedRecords, accounts: CommittedRecords, books: Sequence[str] = BOOKS):
        self.records, self.accounts, self.books = records, accounts, tuple(books)  # accounts: Drive's copy (E2c)

    def status(self, day: date) -> StatusReading:
        used, missing = [], []
        at_paper = self._at_paper(used, missing)
        trades = self._trade_counts(used, missing)
        if at_paper is None or missing:
            code, reason = CARD_DATA_CHECK_FAILED, REASONS[CARD_DATA_CHECK_FAILED]
        elif at_paper:
            code = CARD_TRADE_FIELDS_NOT_BUILT
            reason = REASONS[code].format(count=len(at_paper), names=", ".join(at_paper))
        else:
            code, reason = CARD_NO_APPROVED_STRATEGY, REASONS[CARD_NO_APPROVED_STRATEGY]
        lines = (f"Status: {CardStatus.NO_TRADE} ({code})", f"Reason: {reason}", trades)
        return StatusReading(CardStatus.NO_TRADE, code, CardSection("status", lines, tuple(used), tuple(missing)))

    def _at_paper(self, used: list, missing: list) -> list[str] | None:
        """`name-vN` of every version whose latest registry row is `paper`; None when the registry is unreadable."""
        data = self.records.read(REGISTRY_PATH)
        if data is None:
            missing.append(NOT_READ.format(path=REGISTRY_PATH, why="not committed"))
            return None
        try:
            rows = parse_rows(data.decode("utf-8"))
        except (PlaybookError, UnicodeDecodeError) as bad:
            missing.append(NOT_READ.format(path=REGISTRY_PATH, why=type(bad).__name__))
            return None
        used.append(UsedRecord.of(REGISTRY_PATH, data))
        latest = {row.key: row for row in rows}  # the latest row of a version decides its status (D1)
        return [version_tag(*key) for key, row in sorted(latest.items()) if row.status == PlaybookStatus.PAPER]

    def _trade_counts(self, used: list, missing: list) -> str:
        counts = {book: self._trades_of(book, used, missing) for book in self.books}
        known = [n for n in counts.values() if n is not None]
        total = sum(known) if len(known) == len(counts) else f"at least {sum(known)}"
        books = ", ".join(f"{book} {'unknown' if n is None else n}" for book, n in counts.items())
        return TRADES_LINE.format(total=total, books=books)

    def _trades_of(self, book: str, used: list, missing: list) -> int | None:
        """Open plus closed trades in the book's downloaded account view; None (and named missing) when unreadable."""
        path = POSITIONS_PATH.format(book=book)
        data = self.accounts.read(path)
        if data is None:
            missing.append(NOT_READ.format(path=path, why="not downloaded from Drive"))
            return None
        try:
            view = json.loads(data)
            count = len(view["open_trades"]) + len(view["closed_trades"])
        except (ValueError, KeyError, TypeError) as bad:
            missing.append(NOT_READ.format(path=path, why=type(bad).__name__))
            return None
        used.append(UsedRecord.of(path, data))
        return count
