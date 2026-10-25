"""The risk rule interface (story C2): `check(proposal, book, market) -> RiskVerdict(ok, reason, numbers)`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field

from .inputs import Market, Proposal, RiskBook


@dataclass(frozen=True)
class RiskVerdict:
    rule: str
    ok: bool
    reason: str
    numbers: Mapping[str, object] = field(default_factory=dict)


class RiskRule(ABC):
    """One owner limit or risk check. A rule reads only the book it is given: the proposal's own book."""

    name: str

    @abstractmethod
    def check(self, proposal: Proposal, book: RiskBook, market: Market) -> RiskVerdict:
        """Whether the proposal may open in this book today, with the reason and the numbers behind it."""

    def verdict(self, ok: bool, reason: str, **numbers: object) -> RiskVerdict:
        return RiskVerdict(self.name, ok, reason, numbers)


def rupees(value: float) -> str:
    return f"Rs {value:,.2f}"
