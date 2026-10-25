"""One session's NIFTY option chain by expiry (story P9, W13's contract), from NSE's daily F&O file: each strike's call
and put at the close, and each expiry's summary (put-call ratio, max pain, ATM strike and IV, straddle, the range it
prices in, the walls and where open interest was added). Computed as W13's examples were (the mockup's chain_data.py):
contracts within 10% of the day's NIFTY, expiries of the next three calendar months, strikes with both legs."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from .chain_math import bounded_iv, chance_beyond, rounded_greeks, years_to

SYMBOL = "NIFTY"
STRIKE_BAND = 0.10  # strikes within 10% of the day's NIFTY ("all")
MONTHS_AHEAD = 2  # expiries up to the end of the second month after the session's (on 12 Oct 2026: 31 Dec)
WEEKLY_MONTH = "123456789OND"  # NSE's month letter in a weekly contract's code
CALL, PUT, FUTURE = "CE", "PE", "FUT"


@dataclass(frozen=True)
class FoRow:
    day: date
    expiry: date
    strike: float
    kind: str  # CE, PE or FUT
    close: float
    prev_close: float
    oi: int
    oi_chg: int
    volume: int
    underlying: float
    lot: int


def nifty_rows(day: date, raw: list[dict[str, str]]) -> list[FoRow]:
    """The NIFTY index futures and options of one UDiFF file."""
    return [_row(day, r) for r in raw if r["TckrSymb"] == SYMBOL and r["FinInstrmTp"] in ("IDO", "IDF")]


def _row(day: date, r: dict[str, str]) -> FoRow:
    return FoRow(
        day, date.fromisoformat(r["XpryDt"]), float(r["StrkPric"] or 0), r["OptnTp"] or FUTURE, float(r["ClsPric"]),
        float(r["PrvsClsgPric"] or 0), int(float(r["OpnIntrst"])), int(float(r["ChngInOpnIntrst"])),
        int(float(r["TtlTradgVol"])), float(r["UndrlygPric"]), int(float(r["NewBrdLotQty"])),
    )  # fmt: skip


def in_scope(rows: list[FoRow], day: date, spot: float) -> list[FoRow]:
    """Expiries after the session up to the end of its second following month; options within 10% of the spot."""
    month = day.month + MONTHS_AHEAD
    year, month = day.year + (month - 1) // 12, (month - 1) % 12 + 1
    last = date(year, month, calendar.monthrange(year, month)[1])
    return [r for r in rows if day < r.expiry <= last and (r.kind == FUTURE or abs(r.strike / spot - 1) <= STRIKE_BAND)]


def monthly_expiries(rows: list[FoRow]) -> set[date]:
    """The last expiry of each month among the rows (NSE's monthly contract)."""
    latest: dict[tuple[int, int], date] = {}
    for r in rows:
        key = (r.expiry.year, r.expiry.month)
        latest[key] = max(latest.get(key, r.expiry), r.expiry)
    return set(latest.values())


def contract_code(expiry: date, strike: float, kind: str, monthly: bool) -> str:
    """NIFTY26OCT22300CE for a monthly expiry, NIFTY26O1322300CE (year, month letter, day) for a weekly."""
    when = expiry.strftime("%b").upper() if monthly else f"{WEEKLY_MONTH[expiry.month - 1]}{expiry.day:02d}"
    return f"{SYMBOL}{expiry:%y}{when}{int(strike)}{kind}"


class ExpiryBuilder:
    def __init__(self, rate: float):
        self.rate = rate

    def block(self, day: date, expiry: date, rows: list[FoRow], spot: float, monthly: bool) -> dict:
        days = (expiry - day).days
        years = years_to(days)
        legs: dict[float, dict[str, FoRow]] = {}
        for r in rows:
            if r.kind in (CALL, PUT):
                legs.setdefault(r.strike, {})[r.kind] = r
        strikes = [
            {"strike": k, **{kind: self.side(legs[k][kind], expiry, spot, years, monthly) for kind in (CALL, PUT)}}
            for k in sorted(legs) if len(legs[k]) == 2
        ]  # fmt: skip
        future = next((r.close for r in rows if r.kind == FUTURE), None)
        return {"expiry": expiry.isoformat(), "days": days, "monthly": monthly, "future": future,
                "stats": summary(strikes, spot), "rows": strikes}  # fmt: skip

    def side(self, r: FoRow, expiry: date, spot: float, years: float, monthly: bool) -> dict:
        iv = bounded_iv(r.close, spot, r.strike, years, self.rate, r.kind) if r.volume else None
        breakeven = r.strike + r.close if r.kind == CALL else r.strike - r.close
        return {
            "code": contract_code(expiry, r.strike, r.kind, monthly), "close": r.close,
            "chg": round(r.close - r.prev_close, 2) if r.prev_close else None,
            "chg_pct": round((r.close / r.prev_close - 1) * 100, 2) if r.prev_close else None,
            "oi": r.oi, "oi_chg": r.oi_chg, "volume": r.volume, "iv": round(iv * 100, 1) if iv else None,
            "greeks": rounded_greeks(spot, r.strike, years, self.rate, iv, r.kind) if iv else None,
            "breakeven": round(breakeven, 2),
            "chance": chance_beyond(spot, breakeven, years, self.rate, iv, r.kind) if iv else None,
        }  # fmt: skip


def summary(strikes: list[dict], spot: float) -> dict:
    """The expiry's figures, the F&O tool's way: put-call ratio, max pain, the ATM straddle and the range it prices in,
    the call wall (most call OI at or above NIFTY) and put wall (below), and where OI was added."""
    atm = min(strikes, key=lambda r: (abs(r["strike"] - spot), r["strike"]))
    straddle = round(atm[CALL]["close"] + atm[PUT]["close"], 2)
    above, below = [r for r in strikes if r["strike"] >= spot], [r for r in strikes if r["strike"] <= spot]
    ivs = [atm[CALL]["iv"], atm[PUT]["iv"]]
    return {
        "pcr": round(sum(r[PUT]["oi"] for r in strikes) / max(1, sum(r[CALL]["oi"] for r in strikes)), 2),
        "max_pain": min((r["strike"] for r in strikes), key=lambda x: _pain(strikes, x)), "atm": atm["strike"],
        "atm_iv": round(sum(ivs) / 2, 1) if all(ivs) else None, "straddle": straddle,
        "range": [round(spot - straddle, 2), round(spot + straddle, 2)],
        "call_wall": _top(above, CALL, "oi"), "put_wall": _top(below, PUT, "oi"),
        "call_add": _top(above, CALL, "oi_chg"), "put_add": _top(below, PUT, "oi_chg"),
    }  # fmt: skip


def _pain(strikes: list[dict], level: float) -> float:
    """What option holders would be paid if NIFTY settled at `level` (max pain: the level where this is least)."""
    return sum(
        max(0, level - r["strike"]) * r[CALL]["oi"] + max(0, r["strike"] - level) * r[PUT]["oi"] for r in strikes
    )


def _top(strikes: list[dict], kind: str, key: str) -> float:
    return max(strikes, key=lambda r: r[kind][key])["strike"]
