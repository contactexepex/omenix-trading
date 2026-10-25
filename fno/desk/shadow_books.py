"""The shadow forward test's accounts behind D2's `ShadowBooks` (owner, 14 Oct 2026, experiment 2 option a; story E6
owns this implementation): each registered research candidate has its own paper account (`risk.paper_account_rs`)
`journal/shadow/<name>-v<n>/account/` (E1's format, firewall and lock), never a book's. Its risk view (C2) and its
trade counts are read from that account only, and its storage is that account folder, which D2's `RealBooks` checks
lies outside every real book's folder."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import date
from pathlib import Path

from ..books.account import PaperAccount
from ..books.paths import account_folder, shadow_account
from ..playbook.schema import Strategy
from ..playbook.shadow import ShadowAccount, ShadowBooks
from ..risk.book_view import load_risk_book
from ..risk.inputs import Market, TradeTerms
from .records import DeskRecords
from .trade_counts import DeskTradeCounts, version_tag


def shadow_name(strategy: Strategy) -> str:
    return shadow_account(version_tag(*strategy.key))


class JournalShadowBooks(ShadowBooks):
    """One day's shadow accounts, valued at that day's market. `terms(account)`: that shadow account's own recorded
    terms (structure, width, lots) of each open trade, as C2 needs them; never another account's (story R3)."""

    def __init__(self, root: Path, market: Market, terms: Callable[[str], Mapping[str, TradeTerms]]):
        self.root, self.market, self.terms = root, market, terms  # terms(account): that account's own (story R3)

    def account(self, strategy: Strategy) -> ShadowAccount:
        name = shadow_name(strategy)
        account = PaperAccount(self.root, name)
        if not account.started:
            raise ValueError(f"{name} has not been started (run the shadow accounts' start step first)")
        book = load_risk_book(self.root, name, self.market, self.terms(name))
        return ShadowAccount(book, DeskTradeCounts(DeskRecords(account)), account_folder(self.root, name))


def start_shadow_accounts(strategies: Iterable[Strategy], day: date, open_writer) -> list[str]:
    """Open each candidate's shadow account once (the paper account's cash, no positions); returns the ones opened now.
    `open_writer(name)` is the composition root's `open_account_writer` for this repository."""
    started = []
    for strategy in strategies:
        with open_writer(shadow_name(strategy)) as writer:
            if writer.start(day):
                started.append(shadow_name(strategy))
    return started
