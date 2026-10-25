"""The shadow forward test's accounts (owner, 14 Oct 2026): each registered research candidate trades on paper in its
own shadow account, never in a book's. `ShadowBooks` (the E side builds it) hands out each candidate's account with
the folder it is stored in; the evaluator refuses any account that is named like a real book or stored in, above or
inside a real book's folder (judge 69), so a misconfigured shadow can never draw on a real account."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ..risk.inputs import RiskBook
from .allocation import StrategyTradeCounts
from .schema import Strategy


@dataclass(frozen=True)
class ShadowAccount:
    book: RiskBook
    counts: StrategyTradeCounts
    storage: Path  # the folder this shadow account is kept in


class ShadowBooks(ABC):
    @abstractmethod
    def account(self, strategy: Strategy) -> ShadowAccount:
        """The research candidate's own shadow paper account (never a book's)."""


class RealBooks:
    """The three books' names and storage folders, which no shadow account may share."""

    def __init__(self, names: Sequence[str], folders: Sequence[Path]):
        self.names, self.folders = frozenset(names), tuple(Path(f).resolve() for f in folders)

    def overlap(self, account: ShadowAccount) -> str | None:
        """Why this shadow account is not separate from every real book, or None when it is."""
        if account.book.name in self.names:
            return f"shadow account is named like the real book {account.book.name!r}"
        storage = Path(account.storage).resolve()
        for folder in self.folders:
            if storage == folder or storage.is_relative_to(folder) or folder.is_relative_to(storage):
                return f"shadow account storage {storage} overlaps the real book folder {folder}"
        return None
