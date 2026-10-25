"""Protocol v4 revision 2: the operative claim rule's critical values (owner decision "3 B", 15 Oct 2026; judge 98
addendum 2). Rule E+D: a member may claim only with at least 12 batches and a batch-means t p-value at or below its
worst-case calibrated threshold.

The threshold for a member at a look is the smallest, over its group's null processes, of the empirical quantile of
the batch t p-value at the look's Holm first step (rate / 15), taken at its 95% lower confidence rank, from 100,000
seeded mean-zero series of the member's actual n. The groups pair each family question with Gaussian nulls (i.i.d.,
AR(1) 0.5, overlapping) and its empirical null from **exposed** 2024-26 data (`v4_size_study.py`): QLIKE V1 and V2
with the trailing 5 vs 20 differences, Brier V6a and V6b with the EWMA-normal vs base-rate differences; V7 has no VIX
null measured and borrows V6b's (reasoning only). A held-out check on fresh seeds measures each threshold's size.
G8 calls `claim_threshold` at each look with the member's n; nothing here reads a v4 outcome.

    python tools/v4_claim_thresholds.py   # writes research/forecasts/v4_claim_thresholds.{json,md}
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_size_study as study  # noqa: E402

from fno.constants import V1_RV_1S, V2_RV_5S, V6_BIG_MOVE_1S, V6_BIG_MOVE_5S, V7_VIX_UP_5S  # noqa: E402
from fno.forecast_v4.confirmatory import MIN_CLAIM_BATCHES  # noqa: E402
from fno.forecast_v4.student_t import t_cdf  # noqa: E402

SERIES = 100_000
GAUSSIAN = ("iid", "ar1", "overlapping")
GROUPS = {
    V1_RV_1S: (5, (*GAUSSIAN, "lognormal", "real_h1")),
    V2_RV_5S: (10, (*GAUSSIAN, "lognormal", "real_h5")),
    V6_BIG_MOVE_1S: (5, (*GAUSSIAN, "brier_v6a")),
    V6_BIG_MOVE_5S: (10, (*GAUSSIAN, "brier_v6b")),
    V7_VIX_UP_5S: (10, (*GAUSSIAN, "brier_v6b")),
}
LOOKS = {"look 1": 0.02, "look 2": 0.03}
FAMILY_SIZE = 15
CALIBRATION_WORD, HOLDOUT_WORD = 55, 77
OUT = study.ROOT / "research" / "forecasts" / "v4_claim_thresholds"


def empirical_nulls() -> dict[str, np.ndarray]:
    real = {"real_h1": study.real_differences(1), "real_h5": study.real_differences(5)}
    return real | {name: study.brier_differences(h) for name, (h, _) in study.BRIER_PROCESSES.items()}


def batch_t_p(x: np.ndarray, block: int) -> np.ndarray:
    """The production rule's p (`confirmatory.batch_means_p`) for each row; a zero SE gives p = 1."""
    t, _, k = study.batch_stats(x, block)
    return np.array([t_cdf(v, k - 1) if np.isfinite(v) else 1.0 for v in t])


def _null_p(process: str, block: int, n: int, word: int, index: int, series: int, nulls: dict) -> np.ndarray:
    rng = np.random.default_rng(np.random.SeedSequence([study.SEED, word, block, n, index]))
    return batch_t_p(study.null_matrix(process, series, n, block, rng, nulls), block)


def claim_threshold(question: str, n: int, rate: float, series: int = SERIES, nulls: dict | None = None) -> float:
    """The member's critical value at a look: the smallest group quantile at rate / 15 (0.0 below 12 batches)."""
    block, processes = GROUPS[question]
    if n // block < MIN_CLAIM_BATCHES:
        return 0.0
    nulls = nulls if nulls is not None else empirical_nulls()
    step = rate / FAMILY_SIZE
    quantiles = []
    for index, process in enumerate(processes):
        p = np.sort(_null_p(process, block, n, CALIBRATION_WORD, index, series, nulls))
        quantiles.append(float(p[conservative_rank(step, series)]))
    return min(quantiles)


def conservative_rank(rate: float, series: int) -> int:
    """The order statistic at the one-sided 95% lower confidence bound of the rate-quantile (binomial, normal
    approximation): Monte Carlo error in the threshold then errs towards fewer claims."""
    expected = rate * series
    return max(0, int(math.floor(expected - 1.645 * math.sqrt(expected * (1 - rate)))))


def held_out_size(question: str, n: int, threshold: float, series: int = SERIES, nulls: dict | None = None) -> float:
    """The worst rejection rate over the group's processes on fresh seeds."""
    block, processes = GROUPS[question]
    nulls = nulls if nulls is not None else empirical_nulls()
    rates = [
        float((_null_p(p, block, n, HOLDOUT_WORD, i, series, nulls) <= threshold).mean())
        for i, p in enumerate(processes)
    ]
    return max(rates)


def outcomes_needed(threshold: float, r: float) -> int | None:
    """Planning only (normal approximation, optimistic under heavy tails): ((z(1 - tau) + z(0.8)) r)^2."""
    if threshold <= 0:
        return None
    z = NormalDist().inv_cdf
    return math.ceil(((-z(threshold) + z(0.8)) * r) ** 2)  # -z(tau) = z(1 - tau), exact for very small tau


def main() -> None:
    nulls, rows = empirical_nulls(), []
    for question, (block, _) in GROUPS.items():
        for n in (2 * block, 125, 250):
            for look, rate in LOOKS.items():
                tau = claim_threshold(question, n, rate, nulls=nulls)
                size = held_out_size(question, n, tau, nulls=nulls) if tau > 0 else 0.0
                nominal = rate / FAMILY_SIZE
                row = {"question": question, "block": block, "n": n, "look": look, "nominal": nominal}
                row |= {"threshold": tau, "held_out_size": size, "tolerance": study.tolerance(nominal, SERIES)}
                row |= {"outcomes_r3": outcomes_needed(tau, 3), "outcomes_r5": outcomes_needed(tau, 5)}
                rows.append(row)
                print(rows[-1], flush=True)
    OUT.with_suffix(".json").write_text(json.dumps({"series": SERIES, "rows": rows}, indent=1) + "\n", encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(rows), encoding="utf-8")


def markdown(rows: list[dict]) -> str:
    lines = [
        "# Protocol v4: rule E+D critical values (`tools/v4_claim_thresholds.py`)",
        "",
        f"{SERIES:,} seeded series per null process; threshold = worst-case quantile at rate / 15; held-out size "
        "on fresh seeds against nominal + 2 Monte Carlo SE; fewer than 12 batches: no claim (threshold 0). "
        "Outcomes needed: normal approximation, planning only.",
        "",
        "| question | L | n | look | nominal | threshold | held-out size | tolerance | within | outcomes r=3 / 5 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        within = "yes" if r["held_out_size"] <= r["tolerance"] else "**no**"
        need = f"{r['outcomes_r3']} / {r['outcomes_r5']}" if r["outcomes_r3"] else "no claim"
        head = f"| {r['question']} | {r['block']} | {r['n']} | {r['look']} | {r['nominal']:.5f} | "
        lines.append(
            head + f"{r['threshold']:.3g} | {r['held_out_size']:.5f} | {r['tolerance']:.5f} | {within} | {need} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
