"""The screener route's filters, sorts and pages, as the W11 contract defines them (story P6, judge 49): ported from
the dashboard's reference (omenix-dashboard tools/api/screener_route.py, at the pinned commit), with which the
contract's examples were built from each example's own query (`x-query`). Used here only to check our stored tables
against those examples; the dashboard's route serves the pages. Pure."""

from __future__ import annotations

from collections.abc import Callable

Row = dict
Query = dict

STOCK_SCREENS: dict[str, Callable[[Row], bool]] = {  # the template's SPRESETS (33 notes row 4)
    "high": lambda r: bool(r["h"]) and r["p"] >= r["h"] * 0.98,
    "low": lambda r: bool(r["l"]) and r["p"] <= r["l"] * 1.02,
    "movers": lambda r: abs(r["d1"] or 0) >= 5,
    "volume": lambda r: (r["va"] or 0) >= 5e4 and r["v"] >= 3 * r["va"],
    "trend": lambda r: (r["m1"] or 0) >= 10,
    "fall": lambda r: (r["m1"] or 0) <= -10,
    "delivery": lambda r: (r.get("dl") or 0) >= 70 and (r["va"] or 0) >= 1e5,
    "oversold": lambda r: r["r"] is not None and r["r"] < 30,
}
BUILDUPS = ("long_buildup", "short_buildup", "short_covering", "long_unwinding")
FNO_SCREENS: dict[str, Callable[[Row], bool]] = {  # the template's FPRESETS (33 notes row 10)
    **{name: (lambda b: lambda r: r["b"] == b)(name) for name in BUILDUPS},
    "ivhigh": lambda r: (r["ivr"] or 0) >= 80,
    "ivlow": lambda r: r["ivr"] is not None and r["ivr"] <= 20,
    "oiup": lambda r: (r["oc"] or 0) >= 5,
    "index": lambda r: r["kind"] == "index",
}
DEFAULT_PERIOD = "m1"


def position_in_range(r: Row) -> float | None:
    """Where the close sits in the 52-week range, 0 to 1 (unrounded, so ties near the high keep their order)."""
    return (r["p"] - r["l"]) / (r["h"] - r["l"]) if r["h"] and r["l"] is not None and r["h"] > r["l"] else None


def volume_ratio(r: Row) -> float | None:
    return r["v"] / r["va"] if r["va"] else None


def _stock_value(q: Query) -> Callable[[Row, str], object]:
    period = q.get("period", DEFAULT_PERIOD)
    keys = {
        "value": lambda r: r["p"] * r["v"], "pos": position_in_range, "abs": lambda r: abs(r["d1"] or 0),
        "vr": volume_ratio, "chg": lambda r: r[period],
    }  # fmt: skip
    return lambda r, key: keys[key](r) if key in keys else r.get(key)


def _fno_value(r: Row, key: str) -> object:
    return r["oi"] * r["fut"] if key == "oi" else r.get(key)


def _missing_low(value, low: float) -> float:
    return value if value is not None else low


def _stock_filter(q: Query) -> Callable[[Row], bool]:
    period, screen = q.get("period", DEFAULT_PERIOD), STOCK_SCREENS.get(q.get("screen"))
    tests = [
        lambda r: q["u"] == "all" or q["u"] in r["u"],
        lambda r: screen is None or screen(r),
        lambda r: "symbols" not in q or r["s"] in q["symbols"],
        lambda r: "pmin" not in q or r["p"] >= q["pmin"],
        lambda r: "pmax" not in q or r["p"] <= q["pmax"],
        lambda r: "cmin" not in q or _missing_low(r[period], -1e9) >= q["cmin"],
        lambda r: "vrmin" not in q or (volume_ratio(r) or 0) >= q["vrmin"],
        lambda r: "dlmin" not in q or (r.get("dl") or 0) >= q["dlmin"],
        lambda r: "rmax" not in q or _missing_low(r["r"], 1e9) <= q["rmax"],
        lambda r: "vamin" not in q or (r["va"] or 0) >= q["vamin"],
    ]
    return lambda r: all(test(r) for test in tests)


def _sorted(rows: list[Row], key: str, value: Callable[[Row, str], object], tie: Callable[[Row], float]) -> list[Row]:
    """Descending, or ascending with a leading minus; a missing value always last; ties by `tie` (descending), then
    by symbol (the stored row order is not part of the contract)."""
    ascending, name = key.startswith("-"), key.lstrip("-")

    def order(r: Row):
        v = value(r, name)
        return v is None, 0 if v is None else (v if ascending else -v), -tie(r), r["s"]

    return sorted(rows, key=order)


def _page(table: dict, rows: list[Row], q: Query) -> dict:
    start = (q["page"] - 1) * q["page_size"]
    return {
        "as_of": table["as_of"], "currency": table["currency"], "total": len(rows), "page": q["page"],
        "page_size": q["page_size"], "rows": rows[start : start + q["page_size"]],
    }  # fmt: skip


def stocks_page(table: dict, q: Query) -> dict:
    """The served stocks page of a stored table for a query (u, screen, period, filters, symbols, sort, page)."""
    rows = [r for r in table["rows"] if _stock_filter(q)(r)]
    return _page(table, _sorted(rows, q["sort"], _stock_value(q), lambda r: r["p"] * r["v"]), q)


def fno_page(table: dict, q: Query) -> dict:
    """The served F&O page of the stored F&O table for a query (screen, symbols, sort, page)."""
    screen = FNO_SCREENS.get(q.get("screen"))
    rows = [
        r for r in table["rows"] if (screen is None or screen(r)) and ("symbols" not in q or r["s"] in q["symbols"])
    ]
    return _page(table, _sorted(rows, q["sort"], _fno_value, lambda r: r["oi"] * r["fut"]), q)
