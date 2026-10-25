"""The India companies the stock tool follows (story P6; W11 2.4 input FollowedCompaniesIndia, orchestrator decision of
13 Oct 2026, judge 40): this repository tags those NSE rows "ours" and counts the "ours" universe over its own rows. A
close uses the latest list dated on or before it, never a later one."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path

LIST_FILE = "{day}.json"


@dataclass(frozen=True)
class FollowedCompanies:
    as_of: date
    companies: frozenset[str]


class FollowedCompaniesSource(ABC):
    @abstractmethod
    def on_or_before(self, day: date) -> FollowedCompanies | None:
        """The latest list dated on or before `day`; None if there is none."""


class FollowedCompaniesFolder(FollowedCompaniesSource):
    """Lists recorded as `<as_of>.json` files in W11's FollowedCompaniesIndia shape (until the stock tool publishes its
    read model, K5-proposed, which becomes a second adapter behind the same interface)."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def on_or_before(self, day: date) -> FollowedCompanies | None:
        dated = sorted(p for p in self.folder.glob("*.json") if date.fromisoformat(p.stem) <= day)
        if not dated:
            return None
        record = json.loads(dated[-1].read_text(encoding="utf-8"))
        return FollowedCompanies(date.fromisoformat(record["as_of"]), frozenset(record["companies"]))
