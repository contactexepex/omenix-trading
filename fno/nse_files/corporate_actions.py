"""Corporate actions from NSE's own list (story P6; judge 42): past prices and volumes are put on today's share basis
before any figure that compares the day with an earlier one (1W to 1Y changes, 52-week high and low, volume average,
RSI). Raw NSE closes jump at a split or bonus (KOTAKBANK's 5:1 split on 14 Jan 2026: 2,132.60 to 421.00).

- A split or consolidation ("Face Value Split ... From Rs 5/- Per Share To Re 1/- Per Share") divides earlier prices
  by old face value / new face value; a bonus a:b (a new shares for b held) by (a + b) / b. Earlier volumes are
  multiplied by the same factor (more shares).
- A demerger divides earlier prices by the previous close / the ex-date open, the price the exchange's pre-open call
  auction discovers for the share without the demerged business (the W11 contract's method). For a stock with
  derivatives (F&O) that auction is NSE's special pre-open session, whose price NSE itself uses for index adjustment;
  for any other stock it is the normal pre-open auction (still exchange-discovered, but noisier: DCMSRIND opened at
  51.00 and closed at 54.52 on its ex-date). Volumes stay (the share count does not change). Without an ex-date trade
  there is no such price: only the sessions from the ex-date on are used (figures needing older ones are null).
- Another scheme of arrangement, an amalgamation or a capital reduction has no ratio in NSE's list: only the sessions
  from its ex-date on are used. A bonus of preference shares ("Scheme Of Arrangement - Bonus NCRPS") is another
  security and changes no equity price, like a dividend.
- Dividends, buy-backs, interest, distributions and rights issues change no price here (price returns, not total
  returns; NSE's list gives no rights adjustment factor and it is small).
Only actions with an ex-date on or before the session are applied (never one announced for later)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import date, datetime
from itertools import pairwise
from math import prod

from ..fo_bhavcopy import BadFile
from .nse_files import EquityBar

FACE_VALUE = re.compile(r"From\s+R[es]+\.?\s*([\d.]+)\s*/-.*?To\s+R[es]+\.?\s*([\d.]+)\s*/-", re.IGNORECASE)
BONUS = re.compile(r"^\s*Bonus\s+(\d+)\s*:\s*(\d+)", re.IGNORECASE)
DEMERGER = "demerger"
PREFERENCE_BONUS = "bonus ncrps"  # preference shares: another security
HISTORY_BREAKS = ("arrangement", "amalgamation", "capital reduction")
EX_DATE_FORMAT = "%d-%b-%Y"
PRICE_DECIMALS = 2
JUMP = (0.55, 1.8)  # a one-session close ratio outside this, with no action in the list, gets its symbol looked up
KIND_RATIO, KIND_DEMERGER, KIND_BREAK, KIND_NONE = "ratio", "demerger", "break", "none"


@dataclass(frozen=True)
class CorporateAction:
    symbol: str
    ex_date: date
    subject: str
    kind: str  # ratio (split, bonus), demerger, break (no ratio anywhere) or none (no price change)
    factor: float | None = None  # a ratio action's divisor of earlier prices

    @property
    def changes_shares(self) -> bool:
        return self.kind != KIND_NONE


def classify(subject: str) -> tuple[str, float | None]:
    """(kind, factor) of an action's description in NSE's list."""
    text = subject.strip().lower()
    if text.startswith(DEMERGER):
        return KIND_DEMERGER, None
    if PREFERENCE_BONUS in text:
        return KIND_NONE, None
    if any(word in text for word in HISTORY_BREAKS):
        return KIND_BREAK, None
    factor = prod(float(old) / float(new) for old, new in FACE_VALUE.findall(subject))
    factor *= prod((int(new) + int(held)) / int(held) for new, held in BONUS.findall(subject))
    return (KIND_RATIO, factor) if factor != 1.0 else (KIND_NONE, None)


def read_corporate_actions(data: bytes, filename: str) -> list[CorporateAction]:
    """Every action in NSE's corporate-actions list (JSON from its website), classified."""
    try:
        records = json.loads(data.decode("utf-8"))
        return [_action(r) for r in records if r.get("exDate") not in (None, "-")]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise BadFile(f"{filename}: not NSE's corporate-actions list ({exc})") from exc


def _action(record: dict) -> CorporateAction:
    ex_date = datetime.strptime(record["exDate"], EX_DATE_FORMAT).date()
    return CorporateAction(record["symbol"], ex_date, record["subject"], *classify(record["subject"]))


def adjusted(bars: list[EquityBar], actions: list[CorporateAction]) -> list[EquityBar]:
    """A symbol's bars on its latest share basis, using the actions with an ex-date up to its last bar: each earlier
    bar divided once by the product of the price factors after it (rounded once), nothing before a history break."""
    inside = [a for a in actions if bars[0].day < a.ex_date <= bars[-1].day and a.changes_shares]
    prices, shares = [], []  # (ex-date, factor): price divisors, and the share-count part of them
    for action in sorted(inside, key=lambda a: a.ex_date):
        factor = action.factor if action.kind == KIND_RATIO else None
        if action.kind == KIND_DEMERGER:
            factor = _demerger_factor(bars, action.ex_date)
        if factor is None:
            bars = [b for b in bars if b.day >= action.ex_date]  # earlier factors no longer touch any bar
            continue
        prices.append((action.ex_date, factor))
        if action.kind == KIND_RATIO:
            shares.append((action.ex_date, factor))
    if not prices:
        return bars
    return [_rebased(b, _after(prices, b.day), _after(shares, b.day)) for b in bars]


def _demerger_factor(bars: list[EquityBar], ex_date: date) -> float | None:
    """Previous close / ex-date open (the pre-open auction's price: the special session for F&O stocks, the normal one
    for others); None without a trade on the ex-date."""
    for before, on in pairwise(bars):
        if on.day == ex_date:
            return before.close / on.open if on.open and before.close else None
    return None


def _after(factors: list[tuple[date, float]], day: date) -> float:
    return prod(factor for ex_date, factor in factors if day < ex_date)


def _rebased(bar: EquityBar, price_factor: float, share_factor: float) -> EquityBar:
    if price_factor == 1.0:
        return bar
    return replace(
        bar,
        close=round(bar.close / price_factor, PRICE_DECIMALS),
        high=round(bar.high / price_factor, PRICE_DECIMALS),
        low=round(bar.low / price_factor, PRICE_DECIMALS),
        volume=round(bar.volume * share_factor),
        open=round(bar.open / price_factor, PRICE_DECIMALS) if bar.open else bar.open,
    )


def unexplained(series: dict[str, list[EquityBar]], actions: list[CorporateAction]) -> list[str]:
    """Symbols with a one-session close jump outside JUMP and no share-count action in the list: NSE's list over a date
    range leaves out some (ETFs such as BANKNIFTY1), so their own lists are looked up. The jump only chooses where to
    look; any adjustment comes from NSE's stated ratio or discovered price."""
    covered = {a.symbol for a in actions if a.changes_shares}
    return sorted(symbol for symbol, bars in series.items() if symbol not in covered and _jumps(bars))


def _jumps(bars: list[EquityBar]) -> bool:
    return any(not JUMP[0] < b.close / a.close < JUMP[1] for a, b in pairwise(bars) if a.close)
