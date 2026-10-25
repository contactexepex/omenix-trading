"""E3's one `OrderBuilder` and one `ExitRules` per daily run, served book by book (story F1t): each book's own parts,
from its story (E5 for Book 1, F5 for Book 2, F6 for Book 3). A book with none wired gets no orders (its entries fail
closed with E3's alert) and no exit rules (it has no trade of its own to exit). A dispatcher decides nothing itself."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from ..desk.daily_ports import ExitRules, OrderBuilder, OrdersRefused
from ..desk.entries import EntryOrder
from ..desk.exit_rules import ExitRule

NO_ORDERS = "no order builder is wired for {book} (its story has not landed)"


class OrdersByBook(OrderBuilder):
    def __init__(self, builders: Mapping[str, OrderBuilder]):
        self.builders = dict(builders)

    def orders(self, book: str, run: Path, decided_at: datetime) -> Sequence[EntryOrder]:
        builder = self.builders.get(book)
        if builder is None:
            raise OrdersRefused(NO_ORDERS.format(book=book))
        return builder.orders(book, run, decided_at)


class ExitRulesByBook(ExitRules):
    def __init__(self, rules: Mapping[str, ExitRules]):
        self.by_book = dict(rules)

    def rules(self, book: str) -> Mapping[str, Sequence[ExitRule]]:
        rules = self.by_book.get(book)
        return rules.rules(book) if rules is not None else {}
