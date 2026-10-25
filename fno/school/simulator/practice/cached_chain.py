"""A small memory in front of a `HistoricalChain` (story MS-SIM-d1): a run reads each archived day once. The drivers'
history window reads the 20-odd sessions before each session, one new session at a time, and a Drive read takes
seconds."""

from datetime import date
from functools import lru_cache

from ..history.ports import DayChain, HistoricalChain

CACHED_DAYS = 96  # per run: about three windows of sessions across the roads' underlyings


class CachedChain:
    def __init__(self, chain: HistoricalChain, size: int = CACHED_DAYS):
        self._day = lru_cache(maxsize=size)(chain.day)

    def day(self, underlying: str, session: date) -> DayChain | None:
        return self._day(underlying, session)
