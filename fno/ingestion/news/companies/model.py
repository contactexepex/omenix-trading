"""The company list, as the rest of the news code sees it (NP3a). Consumers (the feed planner, the tagger, later NSE
company data) take a `CompanyListSource` and never import an adapter: swapping the private file for a database or an
API is one new class and one line in a composition root. The number of companies is whatever the source returns; it is
content, not code."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

STOCK, INDEX = "stock", "index"
KINDS = (STOCK, INDEX)


@dataclass(frozen=True)
class Company:
    """`exclusions`: regular expressions removed from a text before its names are looked for (other companies whose name
    contains this one's). `targeted`: also searched for by name, not only found by tagging."""

    symbol: str
    name: str
    aliases: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    targeted: bool = False
    kind: str = STOCK


@dataclass(frozen=True)
class CompanyList:
    version: int
    companies: tuple[Company, ...]
    sha256: str = ""  # of the bytes the list was read from ("" when the source cannot say)


class CompanyListSource(ABC):
    @abstractmethod
    def companies(self) -> CompanyList: ...
