"""Which instruments the A16h probe subscribes to (story A16h): from Groww's public instrument list, the four indices'
values, their futures (current, next, far) and options by distance from each index's ATM strike, monthly near expiry
first and NIFTY's nearest weekly. Each instrument carries the feed's own subscription keys and a class for the report
(judge 499: coverage by class, not by strike)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import date

INDICES = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")
WEEKLY_INDEX = "NIFTY"  # the only index with weekly expiries
INDEX_SYMBOLS = {"MIDCPNIFTY": "NIFTYMIDSELECT"}  # the index value's own symbol where it differs (checked 23 Oct)
RAMP_DAYS = 92  # the ramp draws on every expiry up to about three months
INDEX, FUTURE, OPTION = "index", "future", "option"
MONTHLY, WEEKLY = "monthly", "weekly"
OPTION_TYPES, FUTURE_TYPE, INDEX_TYPE = ("CE", "PE"), "FUT", "IDX"
FUTURES_KEPT = 3  # current, next, far


@dataclass(frozen=True)
class FeedInstrument:
    kind: str
    underlying: str
    exchange: str
    segment: str
    token: str
    expiry: date | None = None
    strike: float | None = None
    option_type: str = ""
    cycle: str = ""  # options: monthly or weekly

    def subscription(self) -> dict:
        return {"exchange": self.exchange, "segment": self.segment, "exchange_token": self.token}

    def feed_class(self) -> str:
        if self.kind != OPTION:
            return f"{self.kind} {self.underlying}"
        return f"option {self.underlying} {self.cycle} {self.expiry} {self.option_type}"


def is_monthly(expiry: date, expiries: Iterable[date]) -> bool:
    """The last listed expiry of its month."""
    return expiry == max(e for e in expiries if (e.year, e.month) == (expiry.year, expiry.month))


def universe(rows: Iterable[Mapping[str, str]], spots: Mapping[str, float], today: date, side: int,
             every_expiry: bool = False) -> list[FeedInstrument]:  # fmt: skip
    """Index values, futures, then options `side` strikes either side of ATM: each index's nearest monthly expiry and
    NIFTY's nearest weekly (the nearest expiry that is not a monthly); with `every_expiry`, every expiry up to about
    three months (the ramp needs 3,000)."""
    rows = list(rows)
    found = [_index(rows, name) for name in INDICES]
    for name in INDICES:
        futures = sorted((r for r in _derivatives(rows, name, today) if r["instrument_type"] == FUTURE_TYPE),
                         key=lambda r: r["expiry_date"])  # fmt: skip
        found += [_instrument(FUTURE, r) for r in futures[:FUTURES_KEPT]]
        if name in spots:
            found += _near_money(rows, name, spots[name], today, side, every_expiry)
    return [i for i in found if i is not None]


def _near_money(rows, name: str, spot: float, today: date, side: int, every: bool) -> list[FeedInstrument]:
    options = [r for r in _derivatives(rows, name, today) if r["instrument_type"] in OPTION_TYPES]
    expiries = sorted({date.fromisoformat(r["expiry_date"]) for r in options})
    if not expiries:
        return []
    monthly = next(e for e in expiries if is_monthly(e, expiries))
    weekly = next((e for e in expiries if not is_monthly(e, expiries)), None) if name == WEEKLY_INDEX else None
    chosen = (
        [e for e in expiries if (e - today).days <= RAMP_DAYS] if every else [monthly, *([weekly] if weekly else [])]
    )
    picked = []
    for expiry in chosen:
        legs = [r for r in options if r["expiry_date"] == expiry.isoformat()]
        strikes = sorted({float(r["strike_price"]) for r in legs}, key=lambda k: (abs(k - spot), k))[: 2 * side + 1]
        cycle = MONTHLY if is_monthly(expiry, expiries) else WEEKLY
        picked += [replace(_instrument(OPTION, r), cycle=cycle) for r in legs if float(r["strike_price"]) in strikes]
    return picked


def _derivatives(rows, name: str, today: date):
    return (r for r in rows if r["underlying_symbol"] == name and r["segment"] == "FNO" and r["expiry_date"]
            and date.fromisoformat(r["expiry_date"]) >= today)  # fmt: skip


def _index(rows, name: str) -> FeedInstrument | None:
    symbol = INDEX_SYMBOLS.get(name, name)
    row = next((r for r in rows if r["instrument_type"] == INDEX_TYPE and r["trading_symbol"] == symbol), None)
    return _instrument(INDEX, {**row, "underlying_symbol": name}) if row else None


def _instrument(kind: str, row: Mapping[str, str]) -> FeedInstrument:
    expiry = date.fromisoformat(row["expiry_date"]) if row.get("expiry_date") else None
    strike = float(row["strike_price"]) if kind == OPTION else None
    underlying = row.get("underlying_symbol") or row["trading_symbol"]
    return FeedInstrument(kind, underlying, row["exchange"], row["segment"], row["exchange_token"], expiry, strike,
                          row["instrument_type"] if kind == OPTION else "")  # fmt: skip
