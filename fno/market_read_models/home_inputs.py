"""What Home's F&O blocks publish (story P10), read from the F&O tool's own records, never examples: each paper book's
account (E1, `journal/<book>/account/`) and the policies the latest frozen experiment passed (the only way a strategy
becomes approved: owner's rule, protocol)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

from ..books.account import PaperAccount
from ..models import IST

BOOK_FAMILIES = (("rule", "F&O Book 1"), ("hybrid", "F&O Book 2"), ("ai", "F&O Book 3"))  # books 1, 2, 3 (W10)
NO_APPROVED_NOTE = (
    "No F&O strategy has passed testing yet: {experiment} passed no policy, so at 3 pm each F&O book records “no "
    "approved strategy”."
)


@dataclass(frozen=True)
class BookFigures:
    number: int
    family: str
    name: str
    value: float  # the book's latest marked equity on or before the session
    pnl: float
    open_trades: int


@dataclass(frozen=True)
class HomeInputs:
    books: list[BookFigures]
    approved: list[str]  # the policies the latest frozen experiment passed
    approval_note: str
    limit_max: float  # the books' open-risk cap (story C5; C2's stress limit before the owner's 15 Oct decision)


class BooksReader:
    """Each book's figures as of a session, from its own account only (books never share money or results)."""

    def __init__(self, root: Path, books: tuple[str, ...], paper_account_rs: float):
        self.root, self.books, self.paper_account_rs = Path(root), books, paper_account_rs

    def on(self, day: date) -> list[BookFigures]:
        return [self._figures(i + 1, book, day) for i, book in enumerate(self.books)]

    def _figures(self, number: int, book: str, day: date) -> BookFigures:
        family, name = BOOK_FAMILIES[number - 1]
        account = PaperAccount(self.root, book)
        rows = [r for r in account.equity_history() if date.fromisoformat(r["date"]) <= day]
        if not rows:  # the book had not opened by then: its opening balance, nothing traded
            opening = float(account.ledger_rows()[0]["amount_rs"]) if account.started else self.paper_account_rs
            return BookFigures(number, family, name, opening, 0.0, 0)
        start = account.capital(datetime.combine(day, time.max, IST))  # capital in force that day: never pnl (E1b)
        value = float(rows[-1]["marked_equity_rs"])
        return BookFigures(number, family, name, value, round(value - start, 2), int(rows[-1]["open_trades"]))


class FrozenExperimentApprovals:
    """The policies a frozen experiment's decisive run passed (`overall.passing_policies` of its results file)."""

    def __init__(self, results_file: Path, experiment: str):
        self.results_file, self.experiment = Path(results_file), experiment

    def passing(self) -> list[str]:
        return list(json.loads(self.results_file.read_text(encoding="utf-8"))["overall"]["passing_policies"])

    def note(self) -> str:
        passing = self.passing()
        if passing:
            return f"{self.experiment} passed {', '.join(passing)}; a book trades one only once it is approved for it."
        return NO_APPROVED_NOTE.format(experiment=self.experiment)


class HomeInputsReader:
    def __init__(self, books: BooksReader, approvals: FrozenExperimentApprovals, limit_max: float):
        self.books, self.approvals, self.limit_max = books, approvals, limit_max

    def on(self, day: date) -> HomeInputs:
        return HomeInputs(self.books.on(day), self.approvals.passing(), self.approvals.note(), self.limit_max)
