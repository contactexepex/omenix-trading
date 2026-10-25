"""The NIFTY panel's rows of one day (story A3): every NIFTY index option and every NIFTY index future of the day's
F&O records, with that day's Nifty 50 and India VIX closes and the session kind. Values are copied, never rounded: a
price with more than two decimals or a count that is not whole is refused."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..constants import INDEX_FUTURE, INDEX_INDIA_VIX, INDEX_NIFTY_50, INDEX_OPTION, NIFTY_SYMBOL
from ..fo_bhavcopy import BadFile

OPTIONS, FUTURES = "options", "futures"  # the panel's two tables
OPTION_COLUMNS = (
    "date", "expiry", "strike", "type", "close", "settle", "volume", "open_interest", "underlying", "vix",
    "source_format", "session",
)  # fmt: skip
FUTURE_COLUMNS = (
    "date", "expiry", "close", "settle", "volume", "open_interest", "underlying", "source_format", "session",
)  # fmt: skip
TABLE_COLUMNS = {OPTIONS: OPTION_COLUMNS, FUTURES: FUTURE_COLUMNS}
CENTS = Decimal("0.01")
Row = tuple[str, ...]


def cents(text: str) -> str:
    """A price or strike with exactly two decimals; more decimals than two is refused, never rounded."""
    value = Decimal(text)
    if value != value.quantize(CENTS):
        raise BadFile(f"value {text!r} has more than two decimals")
    return str(value.quantize(CENTS))


def whole(text: str) -> str:
    value = Decimal(text)
    if value != value.to_integral_value():
        raise BadFile(f"count {text!r} is not a whole number")
    return str(int(value))


def nifty_rows(
    day: date, records: list[dict], closes: dict[str, float], label: str, session: str
) -> dict[str, list[Row]]:
    """Both tables' rows of one day, sorted (options by expiry, strike and type; futures by expiry). A contract listed
    twice, or a row dated another day, raises BadFile."""
    index = (cents(repr(closes[INDEX_NIFTY_50])), cents(repr(closes[INDEX_INDIA_VIX])))
    options: dict[tuple, Row] = {}
    futures: dict[tuple, Row] = {}
    for r in records:
        if r["TckrSymb"] != NIFTY_SYMBOL or r["FinInstrmTp"] not in (INDEX_OPTION, INDEX_FUTURE):
            continue
        if r["TradDt"] != day.isoformat():
            raise BadFile(f"row dated {r['TradDt']} in the file of {day}")
        prices = (cents(r["ClsPric"]), cents(r["SttlmPric"]), whole(r["TtlTradgVol"]), whole(r["OpnIntrst"]))
        if r["FinInstrmTp"] == INDEX_OPTION:
            key = (r["XpryDt"], Decimal(r["StrkPric"]), r["OptnTp"])
            row = (day.isoformat(), r["XpryDt"], cents(r["StrkPric"]), r["OptnTp"], *prices, *index, label, session)
            _add(options, key, row, day)
        else:
            _add(futures, (r["XpryDt"],), (day.isoformat(), r["XpryDt"], *prices, index[0], label, session), day)
    return {OPTIONS: [options[k] for k in sorted(options)], FUTURES: [futures[k] for k in sorted(futures)]}


def _add(rows: dict[tuple, Row], key: tuple, row: Row, day: date) -> None:
    if key in rows:
        raise BadFile(f"duplicate contract {day} {' '.join(map(str, key))}")
    rows[key] = row
