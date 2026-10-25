"""Protocol v4 revision 3: how often the futility rule says a false "no" (orchestrator, after revision 2).

A false "no" can stop the research programme, so it gets the false-"yes" standard. Each empirical null pairs the real
daily loss difference with the real baseline loss (**exposed** 2024-26 NIFTY data; QLIKE V1 and V2: trailing 5 against
trailing 20 sessions, gate set RV > 0 with the baseline's textbook QLIKE; Brier V6a and V6b: EWMA-normal against the
750-session base rate). The difference is centred and shifted so the series' true relative improvement equals the
registered minimum effect exactly (0.03 QLIKE, 0.02 Brier), in both orientations, then resampled jointly in circular
20-session blocks. Rule F0 (revision 1, `bootstrap.effect_check`): futile when the 97.5% bootstrap upper bound is below
the minimum effect; target at most 2.5% per look. Rule F+D (revision 3, `confirmatory.futility_p`): futile only with at
least 12 batches and a batch-means t p-value for "improvement below the effect" at or below a worst-case calibrated
threshold (the 2.5% quantile at its 95% lower confidence rank), computed like `v4_claim_thresholds.py`.

    python tools/v4_futility_study.py   # writes research/forecasts/v4_futility_study.{json,md}
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import v4_claim_thresholds as claims  # noqa: E402
import v4_size_study as study  # noqa: E402

from fno.constants import V1_RV_1S, V2_RV_5S, V6_BIG_MOVE_1S, V6_BIG_MOVE_5S  # noqa: E402
from fno.forecast_v4.confirmatory import futility_p  # noqa: E402
from fno.forecast_v4.terms import BOOTSTRAP_SEED, FUTILITY_CONFIDENCE, LOOK_NUMBER, RESAMPLES  # noqa: E402

SEED, F0_SERIES, CAL_SERIES = 20261015, 10_000, 100_000
QUESTIONS = {V1_RV_1S: ("qlike", 1, 5, 0.03), V2_RV_5S: ("qlike", 5, 10, 0.03),
             V6_BIG_MOVE_1S: ("brier", 1, 5, 0.02), V6_BIG_MOVE_5S: ("brier", 5, 10, 0.02)}  # fmt: skip
LOOKS = ("stop_rule_review", "projected_settle_date")
TARGET = 1 - FUTILITY_CONFIDENCE  # 2.5% per look
OUT = ROOT / "research" / "forecasts" / "v4_futility_study"


def _closes() -> list[dict]:
    with open(ROOT / "research/data/nifty-panel/warmup_closes.csv", encoding="utf-8") as handle:
        return [r for r in csv.DictReader(handle) if r["session"] == "regular" and r["date"] <= "2026-10-14"]


def qlike_pairs(horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """(ranking-loss difference, baseline textbook QLIKE) on the RV > 0 gate dates from 2024."""
    rows = _closes()
    r2 = np.diff(np.log([float(r["underlying"]) for r in rows])) ** 2
    dates = [r["date"] for r in rows][1:]
    d, base = [], []
    for t in range(dates.index(next(x for x in dates if x >= "2024-01-01")), len(r2) - horizon + 1):
        rv, f5, f20 = r2[t : t + horizon].sum(), r2[t - 5 : t].mean() * horizon, r2[t - 20 : t].mean() * horizon
        if f5 > 0 and f20 > 0 and rv > 0:
            d.append(math.log(f5) + rv / f5 - math.log(f20) - rv / f20)
            base.append(rv / f20 - math.log(rv / f20) - 1)
    return np.asarray(d), np.asarray(base)


def brier_pairs(horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """(Brier difference, baseline Brier), as `v4_size_study.brier_differences` but with the baseline's loss."""
    rows = _closes()
    returns = np.diff(np.log([float(r["underlying"]) for r in rows]))
    dates = [r["date"] for r in rows][1:]
    big = np.abs(returns) >= 0.02
    event = np.array([big[t : t + horizon].any() for t in range(len(big) - horizon + 1)])
    ewma = np.empty(len(returns))
    ewma[0] = (returns[:250] ** 2).mean()
    for t in range(1, len(returns)):
        ewma[t] = 0.94 * ewma[t - 1] + 0.06 * returns[t - 1] ** 2
    normal, d, base = NormalDist(), [], []
    for t in range(dates.index(next(x for x in dates if x >= "2024-01-01")), len(event)):
        model = 1 - (1 - 2 * (1 - normal.cdf(0.02 / math.sqrt(ewma[t])))) ** horizon
        rate, y = event[max(0, t - horizon - 749) : t - horizon + 1].mean(), float(event[t])
        d.append((model - y) ** 2 - (rate - y) ** 2)
        base.append((rate - y) ** 2)
    return np.asarray(d), np.asarray(base)


def at_minimum_effect(d: np.ndarray, base: np.ndarray, margin: float, flip: bool) -> np.ndarray:
    """The difference centred (flipped if asked) and shifted so -mean(d) / mean(base) = margin exactly."""
    centred = d - d.mean()
    return (-centred if flip else centred) - margin * base.mean()


def joint_samples(d: np.ndarray, base: np.ndarray, count: int, n: int, rng: np.random.Generator):
    starts = rng.integers(0, len(d), size=(count, math.ceil(n / study.REAL_BLOCK)))
    index = ((starts[:, :, None] + np.arange(study.REAL_BLOCK)) % len(d)).reshape(count, -1)[:, :n]
    return d[index], base[index]


def f0_upper(d: np.ndarray, base: np.ndarray, block: int, k: int, look: str) -> float:
    """`bootstrap.effect_check`'s upper bound from block sums: the same draws as `block_indices` (tested equal)."""
    n, blocks = len(d), math.ceil(len(d) / block)
    rng = np.random.default_rng(np.random.SeedSequence([BOOTSTRAP_SEED, k, 1, LOOK_NUMBER[look]]))
    starts = rng.integers(0, n - block + 1, size=(RESAMPLES, blocks))
    last = n - (blocks - 1) * block
    totals = []
    for values in (d, base):
        cs = np.concatenate(([0.0], np.cumsum(values)))
        full = cs[starts[:, :-1] + block] - cs[starts[:, :-1]]
        totals.append(full.sum(axis=1) + cs[starts[:, -1] + last] - cs[starts[:, -1]])
    ratios = np.sort(-totals[0] / totals[1])
    return float(ratios[math.ceil(FUTILITY_CONFIDENCE * RESAMPLES) - 1])


def pairs_for(question: str) -> tuple[np.ndarray, np.ndarray]:
    kind, horizon, _, _ = QUESTIONS[question]
    return qlike_pairs(horizon) if kind == "qlike" else brier_pairs(horizon)


def futility_threshold(question: str, n: int, series: int = CAL_SERIES) -> float:
    """F+D's critical value: the smallest, over both orientations, of the conservative 2.5% quantile."""
    _, _, block, margin = QUESTIONS[question]
    if n // block < 12:
        return 0.0
    d, base = pairs_for(question)
    quantiles = []
    for flip in (False, True):
        rng = np.random.default_rng(np.random.SeedSequence([SEED, 66, block, n, int(flip)]))
        xd, xb = joint_samples(at_minimum_effect(d, base, margin, flip), base, series, n, rng)
        p = np.sort(_futility_p_rows(xd, xb, block, margin))
        quantiles.append(float(p[claims.conservative_rank(TARGET, series)]))
    return min(quantiles)


def _futility_p_rows(xd: np.ndarray, xb: np.ndarray, block: int, margin: float) -> np.ndarray:
    """`confirmatory.futility_p`'s raw batch t p-value for each row (threshold 1, so p itself)."""
    return claims.batch_t_p(-(xd + margin * xb), block)  # e < 0 means improvement below the effect


def run_cell(question: str, n: int, flip: bool, cell: int, threshold: float) -> dict:
    _, _, block, margin = QUESTIONS[question]
    d, base = pairs_for(question)
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 88, cell]))
    xd, xb = joint_samples(at_minimum_effect(d, base, margin, flip), base, F0_SERIES, n, rng)
    f0 = {look: float(np.mean([f0_upper(xd[i], xb[i], block, i + 1, look) < margin for i in range(F0_SERIES)]))
          for look in LOOKS}  # fmt: skip
    hold = np.random.default_rng(np.random.SeedSequence([SEED, 99, cell]))
    hd, hb = joint_samples(at_minimum_effect(d, base, margin, flip), base, CAL_SERIES, n, hold)
    fd = float(np.mean([futility_p(hd[i], hb[i], block, margin, threshold) <= TARGET for i in range(CAL_SERIES)]))
    return {"question": question, "n": n, "orientation": "flipped" if flip else "as measured", "f0": f0, "fd": fd,
            "threshold": threshold}  # fmt: skip


def main() -> None:
    cells, number = [], 0
    for question in QUESTIONS:
        for n in (125, 250):
            threshold = futility_threshold(question, n)
            for flip in (False, True):
                cells.append(run_cell(question, n, flip, number, threshold))
                number += 1
                print(cells[-1], flush=True)
    data = {"seed": SEED, "f0_series": F0_SERIES, "fd_series": CAL_SERIES, "target": TARGET, "cells": cells}
    OUT.with_suffix(".json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(data), encoding="utf-8")


def markdown(data: dict) -> str:
    tol_f0 = study.tolerance(data["target"], data["f0_series"])
    tol_fd = study.tolerance(data["target"], data["fd_series"])
    lines = [
        "# Protocol v4: false-futility rate at the minimum effect (`tools/v4_futility_study.py`)",
        "",
        f"True improvement = the registered minimum effect; target at most {100 * data['target']:.1f}% per look. "
        f"F0: {data['f0_series']:,} series (tolerance {100 * tol_f0:.2f}%); F+D: {data['fd_series']:,} held-out "
        f"series (tolerance {100 * tol_fd:.2f}%). **Bold** = above tolerance. Exposed 2024-26 data.",
        "",
        "| question | n | orientation | F0 look 1 | F0 look 2 | F+D (both looks) | F+D threshold |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in data["cells"]:
        f0 = [_mark(c["f0"][look], tol_f0) for look in LOOKS]
        row = f"| {c['question']} | {c['n']} | {c['orientation']} | {f0[0]} | {f0[1]} | {_mark(c['fd'], tol_fd)} | "
        lines.append(row + f"{c['threshold']:.3g} |")
    return "\n".join(lines) + "\n"


def _mark(rate: float, tolerance: float) -> str:
    text = f"{100 * rate:.2f}%"
    return f"**{text}**" if rate > tolerance else text


if __name__ == "__main__":
    main()
