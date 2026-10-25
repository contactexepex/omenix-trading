"""`HistoricalChain` over the archived NSE F&O files (story MS-SIM-a): the first file that covers the day, current
format first, as the NIFTY panel and EDGE1 read them. Nothing is guessed: a lot is NSE's `NewBrdLotQty` where the file
states it, never derived from turnover; a day with no readable file, or none for the underlying, is None."""

from collections.abc import Callable, Sequence
from datetime import date

from ....constants import INDEX_FUTURE, INDEX_OPTION
from ....fo_bhavcopy import BadFile, read_fo_file
from ....research_data.nifty_panel import DailyFiles
from ...constants import OptionKind
from .ports import ChainRow, DayChain

IndexCloses = Callable[[str, date], float | None]  # (underlying, session) -> that index's close


def _number(text: str) -> float:
    try:
        return float(text) if text not in ("", "-") else 0.0
    except ValueError as error:
        raise BadFile(f"not a number: {text!r}") from error


class BhavcopyChain:
    def __init__(self, fo_files: Sequence[DailyFiles], index_close: IndexCloses | None = None):
        self.fo_files, self.index_close = fo_files, index_close

    def day(self, underlying: str, session: date) -> DayChain | None:
        for files in self.fo_files:
            if not files.covers(session):
                continue
            name, data = files.get(session)
            if data is None:
                continue
            try:
                chain = self._chain(session, underlying, read_fo_file(name, data), files.label)
            except BadFile:
                continue  # a damaged file, or a number that is not one, is never read partly
            if chain.rows:
                return chain
        return None

    def _chain(self, session: date, underlying: str, records: Sequence[dict], source: str) -> DayChain:
        mine = [r for r in records if r["TckrSymb"] == underlying and r["FinInstrmTp"] in (INDEX_OPTION, INDEX_FUTURE)]
        monthly = {_expiry(r) for r in mine if r["FinInstrmTp"] == INDEX_FUTURE}
        rows, lots, underlying_prices = [], {}, {}
        for r in mine:
            expiry = _expiry(r)
            board = int(_number(r.get("NewBrdLotQty") or ""))
            if board > 0:
                lots.setdefault(expiry, board)
            if r["FinInstrmTp"] == INDEX_OPTION:
                rows.append(_row(r, expiry in monthly))
                underlying_prices.setdefault(expiry, []).append(_number(r.get("UndrlygPric") or ""))
        return DayChain(
            session, underlying, self._close(underlying, session, underlying_prices), tuple(rows), lots, source
        )

    def _close(self, underlying: str, session: date, prices: dict[date, list[float]]) -> float | None:
        """The underlying price the nearest expiry's rows state, so the row order of far expiries cannot change it."""
        nearest = prices[min(prices)] if prices else []
        stated = next((p for p in nearest if p > 0), None)
        return stated if stated is not None else (self.index_close(underlying, session) if self.index_close else None)


def _expiry(record: dict) -> date:
    return date.fromisoformat(record["XpryDt"][:10])


def _row(record: dict, monthly: bool) -> ChainRow:
    return ChainRow(
        _expiry(record), _number(record["StrkPric"]), OptionKind(record["OptnTp"]), _number(record["ClsPric"]),
        int(_number(record["TtlTradgVol"])), int(_number(record["OpnIntrst"])), monthly,
    )  # fmt: skip
