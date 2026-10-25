"""One chain source per underlying (the end-of-day back-fill: G13's panel for NIFTY, the bhavcopy for BANKNIFTY)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from ..price_distribution.chain import ChainDay, ChainSource


class RoutedChains(ChainSource):
    def __init__(self, sources: Mapping[str, ChainSource]):
        self.sources = dict(sources)

    def chain(self, underlying: str, day: date) -> ChainDay | None:
        source = self.sources.get(underlying)
        return source.chain(underlying, day) if source is not None else None
