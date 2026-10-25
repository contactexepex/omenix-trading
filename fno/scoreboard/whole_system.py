"""Scoreboard B, whole systems (story S2, design 12.5): each book's real paper account with every detail, per segment
and overall, pilot evidence apart, under the protocol's rules. Output: `research/scoreboards/B/<date>.json`, canonical
JSON, so a rebuild from the same records gives the same bytes. It reads records only and writes nothing else. Runs the
desk saw but did not collect, corrections included, are listed apart (`uncollected_runs`, story D3b): never scored."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from pathlib import Path

from ..desk.records import DeskRecords
from .book_board import BookBoard, BookInputs
from .book_trades import ScoredTrade, Sessions, book_trades
from .daily_values import DayMarks
from .entry_decisions import EntryDecisions
from .ports import OperatingCosts, ProtocolStatus
from .reconcile import reconciliation
from .series import held_at_close

MissedRuns = Callable[[str, Sequence[date], Callable[[date], bool]], list[dict]]

KIND = "scoreboard_b"
OUTPUT_FOLDER = "research/scoreboards/B"
NOT_STARTED = "account not started"


class WholeSystemBoard:
    def __init__(
        self, books: Sequence[str], records: Callable[[str], DeskRecords], decisions: Callable[[], EntryDecisions],
        sessions: Sessions, marks: DayMarks, costs: OperatingCosts, board: BookBoard, charges: Mapping[str, float],
        protocol: ProtocolStatus, inputs: Callable[[], dict[str, str]],
        uncollected: Callable[[Sequence[str]], dict[str, list[dict]]], missed: MissedRuns | None = None,
    ):  # fmt: skip
        self.books, self.records, self.decisions, self.sessions, self.marks = books, records, decisions, sessions, marks
        self.costs, self.board, self.charges, self.protocol, self.inputs = costs, board, charges, protocol, inputs
        self.uncollected, self.missed = uncollected, missed

    def build(self, on: date) -> dict:
        decisions = self.decisions()
        common_start = decisions.common_start(self.books)
        books = {book: self._book(book, decisions, common_start, on) for book in self.books}
        return {
            "kind": KIND, "date": on.isoformat(), "protocol": self.protocol.label,
            "common_start": common_start.isoformat() if common_start else None, "books": books,
            "inputs_sha256": self.inputs(), "uncollected_runs": self.uncollected(self.books),
            "missed_runs": {book: entry.get("missed_runs", []) for book, entry in books.items()},
        }  # fmt: skip

    def _book(self, book: str, decisions: EntryDecisions, common_start: date | None, on: date) -> dict:
        records = self.records(book)
        if not records.account.started:
            return {"account": NOT_STARTED}
        trades = tuple(book_trades(records, decisions, self.sessions, self.marks, self.charges, on))
        costs = tuple(self.costs.rows(book))
        opened = date.fromisoformat(records.account.ledger_rows()[0]["filled_at"][:10])
        inputs = BookInputs(book, trades, costs, opened, on)
        board = self.board.build(inputs, common_start)
        missed = self._missed(book, trades, opened, on)
        return {"account": "started", **board, "reconciliation": reconciliation(records.account, trades, costs),
                "missed_runs": missed}  # fmt: skip

    def _missed(self, book: str, trades: Sequence[ScoredTrade], first: date, on: date) -> list[dict]:
        if self.missed is None:
            return []
        held = lambda day: any(held_at_close(t, day) for t in trades)  # noqa: E731
        return self.missed(book, self.sessions(first, on), held)


def canonical(board: dict) -> str:
    return json.dumps(board, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def write_board(root: Path, board: dict) -> Path:
    path = Path(root) / OUTPUT_FOLDER / f"{board['date']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical(board), encoding="utf-8")
    return path
