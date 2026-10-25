"""Where 15-minute snapshots come from (design 2.1's `IntradayQuoteSource`): one adapter per source, Groww today."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from .document import SnapshotDocument


class IntradayQuoteSource(ABC):
    name: str

    @abstractmethod
    def prepare(self, session: date) -> None:
        """Everything that can be done before the mark (sign-in, which expiries), so the index request goes out on
        time. Never raises: a failure is kept and reported in the next snapshot."""

    @abstractmethod
    def take(self, session: date, mark: datetime) -> SnapshotDocument:
        """One snapshot now: the index first, then the near future, the chains and the contract quotes. Never
        raises: every failed call is in the document by name."""
