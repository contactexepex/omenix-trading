"""Protocol v4 revision 2: size of the confirmatory test and of its candidate fixes (judge 98 addendum 2).

Seeded and deterministic. Per process, block length L in (5, 10, 20) and n in (2L, 125): 100,000 mean-zero series for
the thresholds below 0.01 and the first 10,000 of them for the rest, B = 10,000. The studentized bootstrap runs only
where a batch t test already rejects at the largest threshold of its tier (the judge's conditional method): a test whose
p is the max of the two cannot reject otherwise, so the rates are exact for every threshold in that tier.

Processes: i.i.d., AR(1) 0.5 and overlapping-horizon Gaussian; the centred lognormal (the judge's skew case); and two
empirical nulls built from **exposed** 2024-26 NIFTY close-proxy data: the centred QLIKE difference of two baselines
(trailing 5 against trailing 20 sessions, horizons 1 and 5, the right-skewed orientation), resampled in circular blocks
of 20 sessions. Options: A max(batch t, studentized bootstrap); B the same at a stricter threshold (Holm step / c);
C max(Hall's skew-corrected batch t, studentized bootstrap); D = A or C with at least 12 batches before a claim.

    python tools/v4_size_study.py      # about 40 minutes; writes research/forecasts/v4_size_study.{json,md}
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fno.forecast_v4.confirmatory import hall_t, studentized_bootstrap_p  # noqa: E402
from fno.forecast_v4.student_t import t_cdf  # noqa: E402

SEED = 20261015
SMALL_TIER, LARGE_TIER = 100_000, 10_000
STEPS = (15, 10, 5, 1)  # Holm steps j: threshold = look rate / j
LOOK_RATES = (0.02, 0.03)
SMALL = tuple(sorted(rate / j for rate in LOOK_RATES for j in STEPS if rate / j < 0.01))
LARGE = tuple(sorted(rate / j for rate in LOOK_RATES for j in STEPS if rate / j >= 0.01))
DIVISORS = (2, 4, 10)
PROCESSES = ("iid", "ar1", "overlapping", "lognormal", "real_h1", "real_h5")
BRIER_PROCESSES = {"brier_v6a": (1, 5), "brier_v6b": (5, 10)}  # horizon, the family block length
OUT = ROOT / "research" / "forecasts" / "v4_size_study"
REAL_BLOCK, AR_PHI = 20, 0.5


def real_differences(horizon: int) -> np.ndarray:
    """Trailing-5 minus trailing-20 QLIKE differences, 2024-01-01 to 2026-10-14, centred (exposed data)."""
    with open(ROOT / "research/data/nifty-panel/warmup_closes.csv", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["session"] == "regular" and r["date"] <= "2026-10-14"]
    r2 = np.diff(np.log([float(r["underlying"]) for r in rows])) ** 2
    dates = [r["date"] for r in rows][1:]
    out = []
    for t in range(dates.index(next(d for d in dates if d >= "2024-01-01")), len(r2) - horizon + 1):
        rv, f5, f20 = r2[t : t + horizon].sum(), r2[t - 5 : t].mean() * horizon, r2[t - 20 : t].mean() * horizon
        if f5 > 0 and f20 > 0:
            out.append(math.log(f5) + rv / f5 - math.log(f20) - rv / f20)
    d = np.asarray(out)
    return d - d.mean()


def brier_differences(horizon: int) -> np.ndarray:
    """Brier(normal-EWMA forecaster) - Brier(750-session base rate) for V6 (|return| >= 2% within `horizon` sessions),
    2024-01-01 to 2026-10-14, centred (exposed data). The forecaster: p = 1 - (1 - 2 (1 - Phi(0.02 / s)))^horizon with
    s the RiskMetrics EWMA (0.94) volatility at the forecast day's close. Oriented to right skew (the worst case)."""
    from statistics import NormalDist

    with open(ROOT / "research/data/nifty-panel/warmup_closes.csv", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["session"] == "regular" and r["date"] <= "2026-10-14"]
    returns = np.diff(np.log([float(r["underlying"]) for r in rows]))
    dates = [r["date"] for r in rows][1:]
    big = np.abs(returns) >= 0.02
    event = np.array([big[t : t + horizon].any() for t in range(len(big) - horizon + 1)])
    ewma = np.empty(len(returns))
    ewma[0] = (returns[:250] ** 2).mean()
    for t in range(1, len(returns)):
        ewma[t] = 0.94 * ewma[t - 1] + 0.06 * returns[t - 1] ** 2
    normal, out = NormalDist(), []
    for t in range(dates.index(next(d for d in dates if d >= "2024-01-01")), len(event)):
        day_p = 2 * (1 - normal.cdf(0.02 / math.sqrt(ewma[t])))
        model = 1 - (1 - day_p) ** horizon
        base = event[max(0, t - horizon - 749) : t - horizon + 1].mean()  # outcomes resolved before day t
        y = float(event[t])
        out.append((model - y) ** 2 - (base - y) ** 2)
    d = np.asarray(out) - np.mean(out)
    return d if (d**3).mean() >= 0 else -d  # the right-skewed orientation, the one that over-rejects


def null_matrix(process: str, count: int, n: int, block: int, rng: np.random.Generator, real: dict) -> np.ndarray:
    if process == "iid":
        return rng.standard_normal((count, n))
    if process == "overlapping":
        span = max(block // 2, 1)
        e = rng.standard_normal((count, n + span - 1))
        return np.stack([e[:, i : i + n] for i in range(span)]).sum(axis=0)
    if process == "ar1":
        e, x = rng.standard_normal((count, n + 200)), np.zeros((count, n + 200))
        for t in range(1, n + 200):
            x[:, t] = AR_PHI * x[:, t - 1] + e[:, t]
        return x[:, 200:]
    if process == "lognormal":
        return np.exp(rng.standard_normal((count, n))) - math.exp(0.5)
    source = real[process]
    starts = rng.integers(0, len(source), size=(count, math.ceil(n / REAL_BLOCK)))
    index = ((starts[:, :, None] + np.arange(REAL_BLOCK)) % len(source)).reshape(count, -1)[:, :n]
    return source[index]


def batch_stats(x: np.ndarray, block: int) -> tuple[np.ndarray, np.ndarray, int]:
    """Batch t and the skewness of the batch means, per series (rows)."""
    k = x.shape[1] // block
    means = x[:, x.shape[1] - k * block :].reshape(len(x), k, block).mean(axis=2)
    centred = means - means.mean(axis=1, keepdims=True)
    sd = means.std(axis=1, ddof=1)
    skew = (centred**3).mean(axis=1) / np.maximum((centred**2).mean(axis=1), 1e-300) ** 1.5
    return means.mean(axis=1) / (sd / math.sqrt(k)), skew, k


def tier_rates(x: np.ndarray, block: int, thresholds: tuple[float, ...], seed_base: int) -> dict:
    t, skew, k = batch_stats(x, block)
    p_t = np.array([t_cdf(v, k - 1) for v in t])
    p_hall = np.array([t_cdf(hall_t(v, g, k), k - 1) for v, g in zip(t, skew, strict=True)])
    top = max(thresholds)
    p_boot = np.ones(len(x))
    for i in np.flatnonzero(np.minimum(p_t, p_hall) <= top):
        p_boot[i] = studentized_bootstrap_p(x[i], block, seed_base + int(i))
    a, c = np.maximum(p_t, p_boot), np.maximum(p_hall, p_boot)
    rates = {"A": [float((a <= h).mean()) for h in thresholds], "C": [float((c <= h).mean()) for h in thresholds]}
    for divisor in DIVISORS:
        rates[f"B/{divisor}"] = [float((a <= h / divisor).mean()) for h in thresholds]
    rates["calibrated_t"] = [_quantile(p_t, h) for h in thresholds]  # the batch-t threshold giving size h
    return rates


def _quantile(p: np.ndarray, rate: float) -> float:
    """The largest order statistic whose rejection rate is at most `rate`: the `allowed`-th smallest p (1-based), so
    rejecting at or below it rejects `allowed` series without ties (0 when none may be rejected)."""
    allowed = int(math.floor(rate * len(p)))
    return float(np.sort(p)[allowed - 1]) if allowed > 0 else 0.0


def repair_calibrated(data: dict) -> dict:
    """Judge 98 addendum 3: the first run's `calibrated_*` columns took the (allowed + 1)-th order statistic. The
    batch-t column is recomputed from the same seeded series with the corrected quantile; `calibrated_A` needs the
    conditional bootstrap again and is dropped (the operative values are in `v4_claim_thresholds.md`)."""
    nulls = {"real_h1": real_differences(1), "real_h5": real_differences(5)}
    nulls |= {name: brier_differences(h) for name, (h, _) in BRIER_PROCESSES.items()}
    for number, cell in enumerate(data["cells"]):
        rng = np.random.default_rng(np.random.SeedSequence([SEED, 98, number]))
        x = null_matrix(cell["process"], data["small_tier"], cell["n"], cell["block"], rng, nulls)
        for tier, rows, thresholds in (("small", x, data["small"]), ("large", x[: data["large_tier"]], data["large"])):
            t, _, k = batch_stats(rows, cell["block"])
            p_t = np.array([t_cdf(v, k - 1) if np.isfinite(v) else 1.0 for v in t])
            cell[tier]["calibrated_t"] = [_quantile(p_t, h) for h in thresholds]
            cell[tier].pop("calibrated_A", None)
    return data


def run_cell(process: str, block: int, n: int, cell: int, real: dict, small: int, large: int) -> dict:
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 98, cell]))
    x = null_matrix(process, small, n, block, rng, real)
    return {"process": process, "block": block, "n": n, "batches": n // block,
            "small": tier_rates(x, block, SMALL, cell * 10_000_000),
            "large": tier_rates(x[:large], block, LARGE, cell * 10_000_000)}  # fmt: skip


def tolerance(rate: float, series: int) -> float:
    return rate + 2 * math.sqrt(rate * (1 - rate) / series)


def plan() -> list[tuple[str, int, int]]:
    """Every process at n = 2L and 125; the skewed ones also at n = 250 for the family's L (5 and 10)."""
    cells = [(p, b, n) for p in PROCESSES for b in (5, 10, 20) for n in (2 * b, 125)]
    cells += [(p, b, 250) for p in ("lognormal", "real_h1", "real_h5") for b in (5, 10)]
    return cells + [(p, b, n) for p, (_, b) in BRIER_PROCESSES.items() for n in (2 * b, 125, 250)]


def main() -> None:
    real = {"real_h1": real_differences(1), "real_h5": real_differences(5)}
    real |= {name: brier_differences(horizon) for name, (horizon, _) in BRIER_PROCESSES.items()}
    done = (
        json.loads(OUT.with_suffix(".json").read_text(encoding="utf-8"))["cells"]
        if OUT.with_suffix(".json").exists()
        else []
    )
    cells = list(done)
    for number, (process, block, n) in enumerate(plan()):
        if number < len(done):
            continue  # resume: a finished cell keeps its seeded result
        cells.append(run_cell(process, block, n, number, real, SMALL_TIER, LARGE_TIER))
        print(process, block, n, cells[-1]["small"]["A"], flush=True)
        _write(cells)


def _write(cells: list[dict]) -> None:
    meta = {"seed": SEED, "small_tier": SMALL_TIER, "large_tier": LARGE_TIER, "small": SMALL, "large": LARGE}
    data = {**meta, "cells": cells}
    OUT.with_suffix(".json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(data), encoding="utf-8")


def markdown(data: dict) -> str:
    """Rejection rates of each option at Holm's first steps (look 1: 0.02/15, look 2: 0.03/15) and at 0.02 and 0.03;
    **bold** = above nominal + 2 Monte Carlo SE; then the calibrated threshold that would give each first-step size."""
    first = [data["small"].index(r / 15) for r in LOOK_RATES]
    last = [data["large"].index(r) for r in LOOK_RATES]
    options = ["A", *[f"B/{d}" for d in DIVISORS], "C"]
    lines = ["# Protocol v4: size of the confirmatory test and its candidate fixes (`tools/v4_size_study.py`)", "",
             f"{data['small_tier']:,} seeded mean-zero series per cell below 0.01, {data['large_tier']:,} above; "
             "B = 10,000; bootstrap only where the batch t rejects (exact for a max test). Columns: look 1 step 1 "
             "(0.00133), look 2 step 1 (0.002), 0.02, 0.03. **Bold** = above nominal + 2 Monte Carlo SE.", "",
             "| process | L | n | batches | " + " | ".join(options) + " | calibrated t: L1, L2 |",
             "|" + "---|" * (5 + len(options))]  # fmt: skip
    for c in data["cells"]:
        row = [f"{c['process']} | {c['block']} | {c['n']} | {c['batches']}"]
        for option in options:
            small = [_cell(c["small"][option][i], data["small"][i], data["small_tier"]) for i in first]
            large = [_cell(c["large"][option][i], data["large"][i], data["large_tier"]) for i in last]
            row.append(" / ".join(small + large))
        row.append(", ".join(f"{c['small']['calibrated_t'][i]:.2g}" for i in first))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def _cell(rate: float, threshold: float, series: int) -> str:
    text = f"{100 * rate:.2f}"
    return f"**{text}**" if rate > tolerance(threshold, series) else text


if __name__ == "__main__":
    if sys.argv[1:] == ["--repair-calibrated"]:
        _write(repair_calibrated(json.loads(OUT.with_suffix(".json").read_text(encoding="utf-8")))["cells"])
    else:
        main()
