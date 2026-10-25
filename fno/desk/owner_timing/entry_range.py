"""The owner's entry rule (story E8 rule 6; owner, 16 Oct 2026, `docs/DESK_DECISIONS.md:220`: "Price cap only"): an
entry fills at the due mark only if its net at the touch is no worse than the decision's approved entry, the limit E4
already enforces (`worse_than_approved`); otherwise it is "missed, price moved". Another rule would be one class here
plus one line in `wiring.py`, through an owner decision and S1."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..entries import EntryOrder, worse_than_approved
from ..execution import FillMaker
from ..pricing import LegQuote


class EntryRange(ABC):
    @abstractmethod
    def admits(self, order: EntryOrder, maker: FillMaker, quotes: list[LegQuote]) -> bool:
        """Whether every-leg quotes at the due mark may fill this entry."""


class ApprovedLimit(EntryRange):
    def admits(self, order: EntryOrder, maker: FillMaker, quotes: list[LegQuote]) -> bool:
        return not worse_than_approved(order, maker, quotes)
