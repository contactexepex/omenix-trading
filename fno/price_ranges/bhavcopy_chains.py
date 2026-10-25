"""Every NIFTY or BANKNIFTY option of a day's archived NSE F&O file (part A7), as a G13 chain: traded closes as prices,
the same-expiry future's close, the three nearest expiries. For the end-of-day back-fill only (`backfill_eod`); the
first archived file that has a day is used, current (UDiFF) format first, as the NIFTY panel does."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from datetime import date

from ..fo_bhavcopy import BadFile, read_fo_file
from ..price_distribution.chain import ChainDay, ChainSource, ExpiryChain, Quote
from ..research_data.nifty_panel import DailyFiles

OPTION, FUTURE = "IDO", "IDF"  # UDiFF instrument codes (legacy files are mapped to them by `read_fo_file`)
EXPIRIES = 3
SOURCE_BHAVCOPY = "bhavcopy"
CLOSE_TIME = "T15:30:00+05:30"


def _number(text: str) -> float | None:
    try:
        return float(text) if text not in ("", "-") else None
    except ValueError:
        return None


class BhavcopyChains(ChainSource):
    def __init__(self, fo_files: Sequence[DailyFiles]):
        self.fo_files = tuple(fo_files)

    def chain(self, underlying: str, day: date) -> ChainDay | None:
        for files in self.fo_files:
            if not files.covers(day):
                continue
            name, data = files.get(day)
            if data is None:
                continue
            try:
                rows = [r for r in read_fo_file(name, data) if r["TckrSymb"] == underlying]
            except BadFile:
                continue
            found = self._chain(underlying, day, rows, name, data)
            if found is not None:
                return found
        return None

    @staticmethod
    def _chain(underlying: str, day: date, rows: list[dict], name: str, data: bytes) -> ChainDay | None:
        options, futures = defaultdict(list), {}
        for r in rows:
            expiry = date.fromisoformat(r["XpryDt"][:10])
            if expiry < day:
                continue
            close, volume = _number(r["ClsPric"]), int(_number(r["TtlTradgVol"]) or 0)
            if r["FinInstrmTp"] == FUTURE:
                futures[expiry] = _number(r["SttlmPric"])  # the same-expiry future's settlement (A7)
            elif r["FinInstrmTp"] == OPTION and r["OptnTp"] in ("CE", "PE"):
                options[expiry].append(Quote(float(r["StrkPric"]), r["OptnTp"], close, volume=volume))
        nearest = sorted(options)[:EXPIRIES]
        if not nearest:
            return None
        spot = next((_number(r["UndrlygPric"]) for r in rows if _number(r["UndrlygPric"])), None)
        expiries = tuple(ExpiryChain(e, tuple(sorted(options[e], key=lambda q: (q.strike, q.kind))), futures.get(e))
                         for e in nearest)  # fmt: skip
        return ChainDay(underlying, day, SOURCE_BHAVCOPY, name, hashlib.sha256(data).hexdigest(),
                        f"{day.isoformat()}{CLOSE_TIME}", spot, expiries)  # fmt: skip
