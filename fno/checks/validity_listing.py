"""NSE's own contract facts for C4 (story C4, judge 83): the newest NSE daily F&O file dated before the decision day
(the previous session's, published that evening). It gives the lot size of every option contract (`NewBrdLotQty`) and
every listed expiry. A monthly expiry is the last listed expiry of its calendar month. Neither comes from the
proposer's settings (`config.yaml` `lot_sizes`) or from A4's choice of chains. No file in the last week fails closed."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta

from ..constants import INDEX_OPTION, NIFTY_SYMBOL
from ..fo_bhavcopy import BadFile, read_fo_file
from ..storage.raw_source import NseDailyFoSource

LOOKBACK_DAYS = 7


def monthly_expiries(expiries: Iterable[str]) -> tuple[str, ...]:
    """NIFTY's monthly expiry is the last of its month: the latest listed expiry in each calendar month."""
    latest: dict[str, str] = {}
    for expiry in expiries:
        latest[expiry[:7]] = max(latest.get(expiry[:7], expiry), expiry)
    return tuple(sorted(latest.values()))


@dataclass(frozen=True)
class Listing:
    file_day: date
    sha256: str
    monthly_expiries: tuple[str, ...]
    lot_sizes: Mapping[str, frozenset[int]]  # expiry ISO -> the lot sizes on its option rows

    def provenance(self) -> dict:
        return {"nse_file_day": self.file_day.isoformat(), "nse_file_sha256": self.sha256}


def _lot(text: str) -> int | None:
    try:
        return int(float(text)) if text else None
    except ValueError:
        return None


def _listing(day: date, data: bytes, underlying: str) -> Listing:
    rows = [
        r
        for r in read_fo_file(NseDailyFoSource.filename_for(day), data)
        if r["FinInstrmTp"] == INDEX_OPTION and r["TckrSymb"] == underlying
    ]
    lots: dict[str, set] = {}
    for r in rows:
        lots.setdefault(r["XpryDt"], set()).add(_lot(r["NewBrdLotQty"]))
    sha = hashlib.sha256(data).hexdigest()
    return Listing(day, sha, monthly_expiries(lots), {e: frozenset(v) for e, v in lots.items()})


class NseListing:
    """Reads through a raw-file library (A2: the project's stores first, then NSE's archive)."""

    def __init__(self, library, underlying: str = NIFTY_SYMBOL):
        self.library, self.underlying = library, underlying

    def read(self, day: date) -> tuple[Listing | None, list[str]]:
        for back in range(1, LOOKBACK_DAYS + 1):
            file_day = day - timedelta(days=back)
            data = self.library.get(NseDailyFoSource.path_for(file_day)).data
            if data is None:
                continue
            try:
                return _listing(file_day, data, self.underlying), []
            except BadFile as problem:
                return None, [f"NSE F&O file of {file_day} unreadable: {problem}"]
        return None, [f"no NSE F&O file in the {LOOKBACK_DAYS} days before {day}"]
