"""G13's score report (section 6): every resolved `ok` row scored against the target session's close, grouped by
label, method hash, horizon and forecaster (labels never pooled), with calibration shares and `implied` compared with
each baseline by G4's moving-block bootstrap (imported unchanged). A row is scored only once its target close is in
the closes file."""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date

from ..forecast_scoring.block_bootstrap import compare
from .constants import FORECAST_LEVELS, HIST750, IMPLIED, OK, RV20
from .records import level_key
from .scoring import quantile_score, share_below, share_inside

SCHEMA = "g13_scores_v1"
NOTE = (
    "descriptive only, no protocol registers these questions; QS is twice the mean pinball loss over 7 levels (a "
    "coarse CRPS approximation), in log-return units; labels are never pooled; secondary to net profit"
)
BASELINES = (RV20, HIST750)
LQ = [level_key(level, "lq") for level in FORECAST_LEVELS]


def forecast_rows(records: Iterable[dict]) -> list[dict]:
    """Every forecast row once (a re-run back-fill repeats identical rows): keyed by label, method, day, forecaster,
    horizon."""
    seen, rows = set(), []
    for record in records:
        for row in record.get("forecasts", []):
            key = (row["label"], row["method_sha256"], row["day"], row["forecaster"], row["horizon"])
            if key not in seen:
                seen.add(key)
                rows.append(row)
    return rows


def resolved(rows: list[dict], closes: Mapping[date, float]) -> list[tuple[dict, float]]:
    """`(row, outcome)` for each ok row whose target close exists: the outcome is `ln(close / s_ref)`."""
    found = []
    for row in rows:
        target = row["target_day"]
        close = closes.get(date.fromisoformat(target)) if target else None
        if row["status"] == OK and close is not None:
            found.append((row, math.log(close / row["s_ref"])))
    return sorted(found, key=lambda pair: pair[0]["day"])


def _group_key(row: dict) -> tuple[str, str, str]:
    return row["label"], row["method_sha256"][:8], row["horizon"]


def group_scores(scored: list[tuple[dict, float]]) -> list[dict]:
    groups = defaultdict(list)
    for row, outcome in scored:
        groups[(*_group_key(row), row["forecaster"])].append((row, outcome))
    out = []
    for (label, method, horizon, forecaster), pairs in sorted(groups.items()):
        outcomes = [y for _, y in pairs]
        scores = [quantile_score(FORECAST_LEVELS, y, [r[k] for k in LQ]) for r, y in pairs]
        coverage = {level_key(t, "q"): share_below(outcomes, [r[k] for r, _ in pairs])
                    for t, k in zip(FORECAST_LEVELS, LQ, strict=True)}  # fmt: skip
        out.append({"label": label, "method": method, "horizon": horizon, "forecaster": forecaster, "n": len(pairs),
                    "first_day": pairs[0][0]["day"], "last_day": pairs[-1][0]["day"],
                    "mean_qs": sum(scores) / len(scores), "share_below": coverage,
                    "central_50": share_inside(outcomes, [r["lq25"] for r, _ in pairs], [r["lq75"] for r, _ in pairs]),
                    "central_90": share_inside(outcomes, [r["lq05"] for r, _ in pairs], [r["lq95"] for r, _ in pairs]),
                    "tail_rows": sum(1 for r, _ in pairs if r["tail_levels"])})  # fmt: skip
    return out


def comparisons(scored: list[tuple[dict, float]]) -> list[dict]:
    """`implied` minus each baseline, daily QS on paired days in date order; negative favours `implied`."""
    by = defaultdict(dict)
    for row, outcome in scored:
        by[(*_group_key(row), row["forecaster"])][row["day"]] = quantile_score(
            FORECAST_LEVELS, outcome, [row[k] for k in LQ]
        )
    out = []
    for group in sorted({key[:3] for key in by}):
        for baseline in BASELINES:
            first, second = by.get((*group, IMPLIED), {}), by.get((*group, baseline), {})
            days = sorted(first.keys() & second.keys())
            k = comparison_seed(*group, baseline)
            result = compare([first[d] - second[d] for d in days], k)
            out.append({"label": group[0], "method": group[1], "horizon": group[2], "first": IMPLIED,
                        "second": baseline, "comparison": k, "n": result.n, "mean_difference": result.mean_difference,
                        "p_value": result.p_value, "interval_unadjusted_95": result.interval,
                        "tested": result.tested})  # fmt: skip
    return out


def comparison_seed(label: str, method: str, horizon: str, baseline: str) -> int:
    """The bootstrap's comparison number from the comparison itself, so a new group never changes another's p."""
    return int(hashlib.sha256(f"{label}|{method}|{horizon}|{baseline}".encode()).hexdigest()[:8], 16)


def score_report(records: Iterable[dict], closes: Mapping[date, float]) -> dict:
    scored = resolved(forecast_rows(records), closes)
    return {"schema": SCHEMA, "note": NOTE, "closes_through": max(closes).isoformat() if closes else None,
            "scored_rows": len(scored), "groups": group_scores(scored), "comparisons": comparisons(scored)}  # fmt: skip


def summary_lines(report: dict) -> list[str]:
    lines = [f"G13 scores: {report['scored_rows']} resolved rows; {report['note']}"]
    for g in report["groups"]:
        lines.append(f"{g['label']} {g['method']} {g['horizon']} {g['forecaster']}: n={g['n']} QS={g['mean_qs']:.5f} "
                     f"90% inside={_share(g['central_90'])} 50% inside={_share(g['central_50'])}")  # fmt: skip
    for c in report["comparisons"]:
        verdict = f"p={c['p_value']:.3f}" if c["tested"] else "not tested (under 40 paired days)"
        diff = "n/a" if c["mean_difference"] is None else f"{c['mean_difference']:+.5f}"
        lines.append(f"{c['label']} {c['horizon']} {c['first']} - {c['second']}: n={c['n']} diff={diff} {verdict}")
    return lines


def _share(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"
