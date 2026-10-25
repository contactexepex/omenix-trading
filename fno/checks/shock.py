"""Where a market shock flag would come from (story C3). The spot check allows a move beyond its limit only on a day
flagged as a shock. Nothing in this repository flags a shock yet (C3 looked: the A6 events file lists scheduled
events, not shocks), so `NoShockFlags` flags none: any move beyond the limit stops new trades until a source exists.
A source (the owner's flag file, an NSE circular feed) is one new class here and one line in the wiring."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

NO_SOURCE = "no shock flag source exists yet"


class ShockFlags(ABC):
    @abstractmethod
    def flagged(self, day: date) -> str:
        """Who flagged the day as a shock and why; empty when it is not flagged."""

    @property
    @abstractmethod
    def source(self) -> str:
        """Where flags come from, named in a failure."""


class NoShockFlags(ShockFlags):
    source = NO_SOURCE

    def flagged(self, day: date) -> str:
        return ""
