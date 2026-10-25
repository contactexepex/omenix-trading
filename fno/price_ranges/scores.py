"""G13b's scores (part A6): QS over the five levels, 50% and 90% band coverage and the Brier score of P(up), per
(label, underlying, issue, horizon, forecaster), from resolved rows only: a live row counts only when sealed, a late
one is counted and never scored. `implied` is compared with each baseline by G4's block bootstrap. G7's consistency
line (implied's N1 P(|r| >= 2%) beside v4's V6a) is reported, never scored."""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from collections.abc import Callable, Iterable

from ..forecast_scoring.block_bootstrap import compare
from ..price_distribution.scoring import quantile_score, share_inside
from .constants import BRIER_NOTE, IMPLIED, LEVELS, LIVE, NO_CHANGE, OK, QS_NOTE, RULE_FORECASTERS, TAU_NOTE
from .records import level_key

SCHEMA = "g13b_scores_v1"
NOTE = "descriptive only, no protocol, no claim; labels, issues and underlyings never pooled; secondary to net profit"
CALIBRATION_MARK = 60  # trading days the owner set for a first calibration read (DESK, 21 Oct)
LQ = [level_key(level, "lq") for level in LEVELS]
GroupKey = tuple[str, str, str, str, str]  # label, method (first 8 of its hash), underlying, issue, horizon


def resolved(records: Iterable[tuple[dict, bool]], close: Callable[[str, str], float | None]) -> tuple[list, int]:
    """`(header, row, outcome)` for each ok row whose target close exists, and the count of late live rows. `records`
    pairs each record with whether it may be scored (a back-fill record, or a sealed live one)."""
    found, late = [], 0
    for record, scorable in records:
        if not scorable:
            late += sum(1 for row in record.get("rows", []) if row["status"] == OK)
            continue
        for row in record.get("rows", []):
            target = close(record["underlying"], row["target_day"]) if row["target_day"] else None
            if row["status"] == OK and target is not None:
                found.append((record, row, math.log(target / row["s_ref"])))  # outcome_close = s_ref x e^y
    return found, late


def _key(record: dict, row: dict) -> GroupKey:
    """A method change is a new version: its rows are scored apart, never pooled (review finding 4)."""
    return record["label"], record["method_sha256"][:8], record["underlying"], record["issue"], row["horizon"]


def _qs(row: dict, outcome: float) -> float:
    return quantile_score(LEVELS, outcome, [row[k] for k in LQ])


def _band(items: list, low: str, high: str) -> float | None:
    ys = [y for _, _, y in items]
    return share_inside(ys, [r[low] for _, r, _ in items], [r[high] for _, r, _ in items])


def _row_brier(row: dict, y: float) -> float:
    """P(up) against "the close is above S_ref" (an equal close is not up)."""
    return (row["p_up"] - (1.0 if y > 0 else 0.0)) ** 2


def _brier(items: list) -> float:
    return sum(_row_brier(r, y) for _, r, y in items) / len(items)


def group_scores(scored: list) -> list[dict]:
    groups = defaultdict(list)
    for record, row, y in scored:
        groups[(*_key(record, row), row["forecaster"])].append((record, row, y))
    out = []
    for (label, method, underlying, issue, horizon, forecaster), items in sorted(groups.items()):
        band = forecaster != NO_CHANGE  # a point mass has no band: "n/a", never 0%
        out.append({
            "label": label, "method": method, "underlying": underlying, "issue": issue, "horizon": horizon,
            "forecaster": forecaster,
            "n": len(items), "days": len({r["day"] for r, _, _ in items}),
            "mean_qs": sum(_qs(row, y) for _, row, y in items) / len(items),
            "inside_50": _band(items, "lq25", "lq75") if band else None,
            "inside_90": _band(items, "lq05", "lq95") if band else None,
            "brier_up": _brier(items),
        })  # fmt: skip
    return out


def _inside(row: dict, y: float, low: str, high: str) -> bool | None:
    return None if row["forecaster"] == NO_CHANGE else row[low] <= y <= row[high]


def row_scores(scored: list) -> list[dict]:
    """One score per resolved row, as FL1 reads them (it never recomputes one): its method (two versions are never
    pooled), the target's official close, the log outcome, QS, both band hits (None for the point mass), its Brier."""
    return [{"label": record["label"], "method_sha256": record["method_sha256"], "underlying": record["underlying"],
             "issue": record["issue"],
             "issue_day": record["day"], "forecaster": row["forecaster"], "horizon": row["horizon"],
             "target_day": row["target_day"], "outcome_close": round(row["s_ref"] * math.exp(y), 2),
             "outcome_log": y, "quantile_score": _qs(row, y), "inside_25_75": _inside(row, y, "lq25", "lq75"),
             "inside_05_95": _inside(row, y, "lq05", "lq95"),
             "brier_up": _row_brier(row, y)} for record, row, y in scored]  # fmt: skip


def comparison_seed(*key: str) -> int:
    return int(hashlib.sha256("|".join(key).encode()).hexdigest()[:8], 16)


def comparisons(scored: list) -> list[dict]:
    """`implied` minus each baseline, daily QS on paired days in date order; negative favours `implied`."""
    by = defaultdict(dict)
    for record, row, y in scored:
        by[(*_key(record, row), row["forecaster"])][record["day"]] = _qs(row, y)
    out = []
    for group in sorted({k[:5] for k in by}):
        for baseline in (f for f in RULE_FORECASTERS if f != IMPLIED):
            first, second = by.get((*group, IMPLIED), {}), by.get((*group, baseline), {})
            days = sorted(first.keys() & second.keys())
            result = compare([first[d] - second[d] for d in days], comparison_seed(*group, baseline))
            out.append({"label": group[0], "method": group[1], "underlying": group[2], "issue": group[3],
                        "horizon": group[4],
                        "first": IMPLIED, "second": baseline, "n": result.n, "mean_difference": result.mean_difference,
                        "p_value": result.p_value, "interval_unadjusted_95": result.interval,
                        "tested": result.tested})  # fmt: skip
    return out


def consistency(records: Iterable[tuple[dict, bool]], v6a: Callable[[str], float | None]) -> list[dict]:
    """Implied's N1 P(|r| >= 2%) beside v4's V6a forecast of the same day (NIFTY only; reported, never scored)."""
    lines = []
    for record, _ in records:
        if record.get("underlying") != "NIFTY":
            continue
        row = next((r for r in record.get("rows", []) if r["forecaster"] == IMPLIED and r["horizon"] == "N1"), None)
        if row is not None and row.get("p_big_move") is not None:
            lines.append({"day": record["day"], "label": record["label"], "implied_p_big_move": row["p_big_move"],
                          "v6a": v6a(record["day"])})  # fmt: skip
    return lines


def score_report(records: list[tuple[dict, bool]], close, v6a=lambda day: None) -> dict:
    scored, late = resolved(records, close)
    live_days = len({r["day"] for r, _, _ in scored if r["label"] == LIVE})
    return {"schema": SCHEMA, "notes": [NOTE, QS_NOTE, TAU_NOTE, BRIER_NOTE], "calibration_mark_days": CALIBRATION_MARK,
            "sealed_live_days": live_days, "late_rows": late, "scored_rows": len(scored),
            "groups": group_scores(scored), "comparisons": comparisons(scored), "rows": row_scores(scored),
            "consistency": consistency(records, v6a)}  # fmt: skip
