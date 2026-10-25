"""The F&O screener's underlying rows (story P6): per F&O underlying, from three months of NSE's daily F&O files
(UDiFF), computed the way the W11 contract's examples were (dashboard design/mockups/33-screener/fetch_nse.py and
_platform/screener_data.py): the nearest monthly expiry's future (price and open-interest change, build-up), the
at-the-money call and put (ATM IV by Black-Scholes on the spot, only legs that traded, and only with 7 or more days
to expiry), the IV's 3-month range and rank, the put-call ratio and the move the straddle prices in."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from ..constants import OPTION_CALL, OPTION_PUT
from ..research_engine.implied_vol import ImpliedVolModel, OptionPricing

FUTURES, OPTIONS = ("STF", "IDF"), ("STO", "IDO")
INDEX_FUTURE = "IDF"
MIN_DAYS_FOR_IV = 7  # an expiry days away gives no sound ATM IV
SHORTEST_YEARS_DAYS = 0.25
DAYS_PER_YEAR = 365
BUILDUPS = ("long_buildup", "short_buildup", "short_covering", "long_unwinding")


@dataclass(frozen=True)
class AtmLeg:
    close: float
    volume: float


@dataclass(frozen=True)
class UnderlyingDay:
    day: date
    symbol: str
    kind: str  # "index" or "stock"
    spot: float
    expiry: date
    fut_close: float
    fut_prev: float
    fut_oi: float
    fut_oi_change: float
    call_oi: int
    put_oi: int
    atm: float
    call: AtmLeg | None
    put: AtmLeg | None
    lot: int


def underlying_days(day: date, rows: list[dict[str, str]]) -> list[UnderlyingDay]:
    """One record per underlying with a future and options on its nearest monthly expiry after `day`."""
    by_symbol: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_symbol.setdefault(row["TckrSymb"], []).append(row)
    return [u for symbol, rs in sorted(by_symbol.items()) if (u := _underlying_day(day, symbol, rs)) is not None]


def _underlying_day(day: date, symbol: str, rows: list[dict[str, str]]) -> UnderlyingDay | None:
    expiries = sorted({r["XpryDt"] for r in rows if r["XpryDt"] > day.isoformat()})
    monthly = [e for e in expiries if e == max(x for x in expiries if x[:7] == e[:7])]
    if not monthly:
        return None
    expiry = monthly[0]
    future = next((r for r in rows if r["FinInstrmTp"] in FUTURES and r["XpryDt"] == expiry), None)
    options = [r for r in rows if r["FinInstrmTp"] in OPTIONS and r["XpryDt"] == expiry]
    if future is None or not options:
        return None
    spot = float(future["UndrlygPric"])
    atm = min({float(r["StrkPric"]) for r in options}, key=lambda k: (abs(k - spot), k))

    def leg(kind: str) -> AtmLeg | None:
        row = next((r for r in options if float(r["StrkPric"]) == atm and r["OptnTp"] == kind), None)
        return None if row is None else AtmLeg(float(row["ClsPric"]), float(row["TtlTradgVol"] or 0))

    return UnderlyingDay(
        day, symbol, "index" if future["FinInstrmTp"] == INDEX_FUTURE else "stock", spot, date.fromisoformat(expiry),
        float(future["ClsPric"]), float(future["PrvsClsgPric"] or 0), float(future["OpnIntrst"]),
        float(future["ChngInOpnIntrst"]), _open_interest(options, OPTION_CALL), _open_interest(options, OPTION_PUT),
        atm, leg(OPTION_CALL), leg(OPTION_PUT), int(future["NewBrdLotQty"]),
    )  # fmt: skip


def _open_interest(options: list[dict[str, str]], kind: str) -> int:
    return sum(int(float(r["OpnIntrst"])) for r in options if r["OptnTp"] == kind)


def buildup(price_change: float, oi_change: float) -> str:
    """Price and open interest moving together or apart (the reading every Indian broker shows)."""
    if oi_change >= 0:
        return BUILDUPS[0] if price_change >= 0 else BUILDUPS[1]
    return BUILDUPS[2] if price_change >= 0 else BUILDUPS[3]


class FnoRowBuilder:
    def __init__(self, model: ImpliedVolModel, rate: float):
        self.model, self.rate = model, rate

    def atm_iv(self, u: UnderlyingDay) -> float | None:
        """Mean IV of the ATM legs that traded, in percent points (one decimal); None with under 7 days to expiry."""
        days = (u.expiry - u.day).days
        if days < MIN_DAYS_FOR_IV:
            return None
        years = max(days, SHORTEST_YEARS_DAYS) / DAYS_PER_YEAR
        ivs = []
        for kind, leg in ((OPTION_CALL, u.call), (OPTION_PUT, u.put)):
            if leg is not None and leg.volume > 0:
                iv = self.model.implied_vol(OptionPricing(leg.close, u.spot, u.atm, kind, years, self.rate))
                if iv:
                    ivs.append(iv)
        return round(sum(ivs) / len(ivs) * 100, 1) if ivs else None

    def rows(self, history: Mapping[str, list[UnderlyingDay]], day: date, names: Mapping[str, str]) -> list[dict]:
        """Every underlying with a record on `day`, by symbol; `history` holds each one's records oldest first."""
        return [self.row(days, names) for symbol, days in sorted(history.items()) if days[-1].day == day]

    def row(self, days: list[UnderlyingDay], names: Mapping[str, str]) -> dict:
        u = days[-1]
        price_change = round((u.fut_close / u.fut_prev - 1) * 100, 2) if u.fut_prev else 0.0
        before = u.fut_oi - u.fut_oi_change
        oi_change = round(u.fut_oi_change / before * 100, 2) if before else 0.0
        series = [iv for iv in map(self.atm_iv, days) if iv is not None]
        iv = self.atm_iv(u)
        low, high = (min(series), max(series)) if series else (None, None)
        rank = round((iv - low) / (high - low) * 100) if iv is not None and len(series) > 1 and high > low else None
        straddle = u.call.close + u.put.close if u.call and u.put else None
        return {
            "s": u.symbol, "n": names.get(u.symbol) or u.symbol, "kind": u.kind, "fut": u.fut_close, "fc": price_change,
            "oi": int(u.fut_oi), "oc": oi_change, "b": buildup(price_change, u.fut_oi_change), "iv": iv, "ivl": low,
            "ivh": high, "ivr": rank, "pcr": round(u.put_oi / u.call_oi, 2) if u.call_oi else None,
            "mv": round(straddle / u.spot * 100, 1) if straddle else None, "x": u.expiry.isoformat(), "lot": u.lot,
        }  # fmt: skip
