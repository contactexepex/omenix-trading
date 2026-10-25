"""The Markets overview's index rows and Nifty 500 industries (story P6), computed the way the W11 contract's
examples were (dashboard design/mockups/34-markets/fetch_nse_indices.py and _platform/markets_data.py): each index's
close, returns on the close 1, 5, 21, 63 and 250 sessions back, 52-week high and low of the closes, NSE's P/E, P/B and
dividend yield, and its last closes; industries as the equal-weighted average change of their Nifty 500 stocks."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from statistics import mean

from .nse_files import IndexFigures
from .stock_rows import PERIOD_BACK, YEAR_SESSIONS

BROAD = ("Nifty 50", "Nifty Next 50", "Nifty 500", "NIFTY Midcap 100", "NIFTY Smallcap 100")
VOLATILITY = "India VIX"
SECTORS = (
    "Nifty Bank", "Nifty Private Bank", "Nifty PSU Bank", "Nifty Financial Services", "Nifty IT", "Nifty Auto",
    "Nifty Pharma", "Nifty Healthcare Index", "Nifty FMCG", "Nifty Metal", "Nifty Realty", "Nifty Energy",
    "Nifty Oil & Gas", "Nifty Media", "Nifty Infrastructure", "Nifty Consumer Durables", "Nifty Capital Goods",
    "Nifty Telecommunications",
)  # fmt: skip
GROUP_BROAD, GROUP_VOLATILITY, GROUP_SECTOR = "broad", "vol", "sector"
SECTOR_CLOSES = 63  # a sector index shows its last 3 months of closes, the others a year


def returns(closes: list[float]) -> dict[str, float | None]:
    last = closes[-1]
    return {
        k: round((last / closes[-1 - n] - 1) * 100, 2) if len(closes) > n and closes[-1 - n] else None
        for k, n in PERIOD_BACK.items()
    }


def group_of(name: str) -> str:
    return GROUP_VOLATILITY if name == VOLATILITY else GROUP_BROAD if name in BROAD else GROUP_SECTOR


def index_rows(sessions: Iterable[tuple[date, dict[str, IndexFigures]]]) -> list[dict]:
    """The broad indices and India VIX first (in that order), then the sectors by the day's change, best first."""
    history: dict[str, list[tuple[date, IndexFigures]]] = {}
    for day, figures in sessions:
        for name in sorted(figures):
            if name in BROAD or name in SECTORS or name == VOLATILITY:
                history.setdefault(name, []).append((day, figures[name]))
    rows = [_row(name, dated) for name, dated in history.items()]
    order = {name: i for i, name in enumerate((*BROAD, VOLATILITY))}
    return sorted(rows, key=lambda r: (order.get(r["name"], len(order)), -(r["d1"] or 0)))


def _row(name: str, dated: list[tuple[date, IndexFigures]]) -> dict:
    """`as_of` is the index's own last figure: a session file without the index never passes its older close off as
    the day's (NSE added two indices to its 12 Oct 2026 file hours after first publishing it)."""
    closes, (as_of, last), group = [f.close for _, f in dated], dated[-1], group_of(name)
    keep = SECTOR_CLOSES if group == GROUP_SECTOR else YEAR_SESSIONS
    return {
        "name": name, "group": group, "as_of": as_of.isoformat(), "close": closes[-1], **returns(closes),
        "hi52": max(closes[-YEAR_SESSIONS:]),
        "lo52": min(closes[-YEAR_SESSIONS:]), "pe": last.pe, "pb": last.pb, "dy": last.dividend_yield,
        "closes": closes[-keep:],
    }  # fmt: skip


def industries(nifty_500_rows: list[dict]) -> list[dict]:
    """Each Nifty 500 industry: its stocks' equal-weighted average change per period, how many rose and fell, and the
    best and worst stock of the day; most stocks first."""
    by_industry: dict[str, list[dict]] = {}
    for row in nifty_500_rows:
        if row["g"]:
            by_industry.setdefault(row["g"], []).append(row)
    out = []
    for name, rows in by_industry.items():
        best, worst = max(rows, key=lambda r: r["d1"] or 0), min(rows, key=lambda r: r["d1"] or 0)
        out.append({
            "g": name, "n": len(rows), **{k: _average(rows, k) for k in PERIOD_BACK},
            "up": sum(1 for r in rows if (r["d1"] or 0) > 0), "down": sum(1 for r in rows if (r["d1"] or 0) < 0),
            "best": [best["s"], best["d1"]], "worst": [worst["s"], worst["d1"]],
        })  # fmt: skip
    return sorted(out, key=lambda x: -x["n"])


def _average(rows: list[dict], key: str) -> float | None:
    values = [r[key] for r in rows if r[key] is not None]
    return round(mean(values), 2) if values else None
