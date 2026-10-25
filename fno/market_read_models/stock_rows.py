"""The screener's stock rows (story P6): one row per EQ or BE stock that traded on the session, from a year of NSE's
daily capital-market files, computed the way the W11 contract's examples were (dashboard
design/mockups/33-screener/fetch_nse.py and _platform/screener_data.py): returns on the close 1, 5, 21, 63 and 250
sessions back, the 52-week high and low over the last 250 sessions (null when a corporate action cut that window),
volume against its 20-session average, Wilder's RSI 14 over the whole window,
delivery %, sector (Nifty 500 industry) and universes."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date

from .nse_files import EquityBar

PERIOD_BACK = {"d1": 1, "w1": 5, "m1": 21, "m3": 63, "y1": 250}  # sessions back for each period's change
YEAR_SESSIONS = 250
VOLUME_SESSIONS = 20
RSI_SESSIONS = 14
UNIVERSE_NIFTY_500, UNIVERSE_FNO, UNIVERSE_FOLLOWED = "n500", "fno", "ours"  # ours: the stock tool follows it


def pct(now: float, then: float | None) -> float | None:
    return round((now / then - 1) * 100, 2) if then else None


def rsi14(closes: list[float]) -> float | None:
    """Wilder's 14-session RSI over all the closes given (the smoothing settles over the window)."""
    if len(closes) <= RSI_SESSIONS:
        return None
    gains = [max(0.0, b - a) for a, b in zip(closes, closes[1:])]
    losses = [max(0.0, a - b) for a, b in zip(closes, closes[1:])]
    up, down = sum(gains[:RSI_SESSIONS]) / RSI_SESSIONS, sum(losses[:RSI_SESSIONS]) / RSI_SESSIONS
    for gain, loss in zip(gains[RSI_SESSIONS:], losses[RSI_SESSIONS:]):
        up = (up * (RSI_SESSIONS - 1) + gain) / RSI_SESSIONS
        down = (down * (RSI_SESSIONS - 1) + loss) / RSI_SESSIONS
    return round(100.0 if down == 0 else 100 - 100 / (1 + up / down), 1)


def stock_series(sessions: Iterable[list[EquityBar]]) -> dict[str, list[EquityBar]]:
    """Each symbol's bars in session order (the sessions given oldest first)."""
    series: dict[str, list[EquityBar]] = defaultdict(list)
    for bars in sessions:
        for bar in bars:
            series[bar.symbol].append(bar)
    return series


def stock_row(
    bars: list[EquityBar], name: str, sector: str, delivery: float | None, universes: list[str], cut: bool = False
) -> dict:
    """`cut`: sessions inside the window were dropped (a corporate action without a price, judge 49), so a figure whose
    window reaches past the first bar left is null, never one over a shorter window. Without a cut, fewer sessions
    mean a later listing: its high since listing is its 52-week high."""
    last, closes = bars[-1], [b.close for b in bars]
    back = {k: closes[-1 - n] if len(closes) > n else None for k, n in PERIOD_BACK.items()}
    year = bars[-YEAR_SESSIONS:] if not cut or len(bars) >= YEAR_SESSIONS else []
    volumes = [b.volume for b in bars[-VOLUME_SESSIONS - 1 : -1]] if not cut or len(bars) > VOLUME_SESSIONS else []
    return {
        "s": last.symbol, "n": name, "g": sector, "p": last.close, **{k: pct(last.close, v) for k, v in back.items()},
        "h": max((b.high for b in year), default=None), "l": min((b.low for b in year), default=None),
        "v": last.volume, "va": float(round(sum(volumes) / len(volumes))) if volumes else None, "dl": delivery,
        "r": rsi14(closes), "u": universes,
    }  # fmt: skip


def stock_rows(
    series: Mapping[str, list[EquityBar]],
    day: date,
    names: Mapping[str, str],
    industries: Mapping[str, str],
    delivery: Mapping[str, float | None],
    fno_symbols: set[str],
    followed: frozenset[str] = frozenset(),
    cut: set[str] = frozenset(),
) -> list[dict]:
    """Every stock that traded on `day`, by symbol. A Nifty 500 industry counts only for a company on NSE's list of
    listed companies (as in the contract's examples)."""
    rows = []
    for symbol, bars in sorted(series.items()):
        if bars[-1].day != day:
            continue
        sector = industries.get(symbol, "") if symbol in names else ""
        memberships = (
            (UNIVERSE_NIFTY_500, bool(sector)),
            (UNIVERSE_FNO, symbol in fno_symbols),
            (UNIVERSE_FOLLOWED, symbol in followed),
        )
        universes = [universe for universe, member in memberships if member]
        name = names.get(symbol) or symbol
        rows.append(stock_row(bars, name, sector, delivery.get(symbol), universes, symbol in cut))
    return rows
