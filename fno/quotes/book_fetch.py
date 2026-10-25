"""One quote book per contract, in order, with each request's own send and receive times (stories A4 and A4c). One
worker reproduces A4's sequential capture exactly; the index slots use a few workers under a shared rate pacer and stop
starting requests at their window's end."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

from ..intraday.pacing import RatePacer
from ..models import OptionChain, QuoteBook
from ..providers.base import Provider

WINDOW_ENDED = "not started: the slot's window had ended"


class WindowEnded(RuntimeError):
    pass


@dataclass(frozen=True)
class Fetched:
    strike: float
    kind: str
    sent: datetime | None
    received: datetime | None
    book: QuoteBook | None
    error: Exception | None


class BookFetcher:
    def __init__(self, provider: Provider, now: Callable[[], datetime], workers: int = 1,
                 pacer: RatePacer | None = None, stop_at: datetime | None = None):  # fmt: skip
        self.provider, self.now, self.workers, self.pacer, self.stop_at = provider, now, workers, pacer, stop_at

    def fetch(self, chain: OptionChain, contracts: list[tuple[float, str]]) -> list[Fetched]:
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            return list(pool.map(lambda contract: self._one(chain, *contract), contracts))

    def _one(self, chain: OptionChain, strike: float, kind: str) -> Fetched:
        if self.pacer is not None:
            self.pacer.wait()
        sent = self.now()
        if self.stop_at is not None and sent > self.stop_at:
            return Fetched(strike, kind, None, None, None, WindowEnded(WINDOW_ENDED))
        try:
            book = self.provider.quote_book(chain, strike, kind)
        except Exception as exc:
            return Fetched(strike, kind, sent, None, None, exc)
        return Fetched(strike, kind, sent, self.now(), book, None)
