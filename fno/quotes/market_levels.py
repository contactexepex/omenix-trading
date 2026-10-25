"""India VIX and the NIFTY futures at the 3 pm capture (story A4, extended for story B7): live F2 needs VIX at the
cutoff and live F1 the same-expiry future, which the option quotes do not carry. Research data only: read-only public
market data, never an order.

`LevelSource` is the interface; `NseLevelSource` reads NSE's public website (`/api/allIndices` for India VIX and
`/api/liveEquity-derivatives?index=nse50_fut` for every listed NIFTY future: last price and volume). Neither carries a
bid or ask; NSE stamps the index list with its own time, which is recorded. A level that cannot be read is recorded as
a failure and never blocks the option capture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from ..constants import INDEX_INDIA_VIX, NIFTY_SYMBOL

ALL_INDICES_PATH = "/api/allIndices"
INDEX_FUTURES_PATH, NIFTY_FUTURES_LIST = "/api/liveEquity-derivatives", "nse50_fut"
NSE_DATE = "%d-%b-%Y"


@dataclass(frozen=True)
class FutureLevel:
    expiry: date
    last: float
    volume: int


@dataclass(frozen=True)
class MarketLevels:
    india_vix: float | None = None
    vix_time: str = ""  # NSE's own timestamp of the index list
    futures: tuple[FutureLevel, ...] = ()
    failures: tuple[str, ...] = field(default=())

    def meta(self) -> dict:
        return {
            "india_vix": self.india_vix, "india_vix_time": self.vix_time, "levels_failures": list(self.failures),
            "futures": [{"expiry": f.expiry.isoformat(), "last": f.last, "volume": f.volume} for f in self.futures],
        }  # fmt: skip


class LevelSource(ABC):
    name: str

    @abstractmethod
    def levels(self, underlying: str) -> MarketLevels:
        """India VIX and the underlying's futures now; failures recorded inside, never raised."""


def parse_india_vix(payload: dict) -> tuple[float | None, str]:
    row = next((r for r in payload.get("data", []) if r.get("index", "").upper() == INDEX_INDIA_VIX.upper()), None)
    return (float(row["last"]) if row and row.get("last") else None), str(payload.get("timestamp", ""))


def parse_index_futures(payload: dict, underlying: str) -> tuple[FutureLevel, ...]:
    rows = [r for r in payload.get("data", []) if r.get("underlying") == underlying and r.get("lastPrice")]
    futures = (
        FutureLevel(
            datetime.strptime(r["expiryDate"], NSE_DATE).date(), float(r["lastPrice"]), int(r.get("volume") or 0)
        )
        for r in rows
    )
    return tuple(sorted(futures, key=lambda f: f.expiry))


class NseLevelSource(LevelSource):
    name = "nse"

    def __init__(self, nse_json: Callable[[str, dict | None], dict]):
        self.nse_json = nse_json

    def levels(self, underlying: str) -> MarketLevels:
        if underlying != NIFTY_SYMBOL:
            return MarketLevels(failures=(f"no futures list for {underlying}",))
        failures, vix, stamp, futures = [], None, "", ()
        try:
            vix, stamp = parse_india_vix(self.nse_json(ALL_INDICES_PATH, None))
        except Exception as exc:  # recorded, never hidden
            failures.append(f"india vix: {type(exc).__name__}: {exc}")
        try:
            futures = parse_index_futures(self.nse_json(INDEX_FUTURES_PATH, {"index": NIFTY_FUTURES_LIST}), underlying)
        except Exception as exc:
            failures.append(f"futures: {type(exc).__name__}: {exc}")
        return MarketLevels(vix, stamp, futures, tuple(failures))
