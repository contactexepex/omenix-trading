"""Protocol v4 revision 4: the Brier rules (V6a, V6b and V7) across regimes (judge 98 addendum 3).

Revision 3 calibrated the Brier rules on 2024-26 only. Here the empirical nulls use **every exposed regular session
with a valid base rate** (at least 500 resolved outcomes: from Jan 2019 to 14 Oct 2026). A **calm-window stress** adds
the calmest 125- and 250-session stretches (fewest 2% days): series are resampled from inside the stretch of the
2019-26 null, which is the realistic danger, an equal-skill forecaster scored in a calm period. Each null pairs the
Brier difference (EWMA-normal forecaster minus the 750-session base rate), the base rate's own Brier loss, and the
2%-day indicator of the outcome's first session; it is resampled jointly in circular 20-session blocks, in both
orientations. Claim nulls are centred; futility nulls are shifted to a true Brier skill of exactly 0.02.

Candidate gate M(m): no Brier claim or futility verdict unless the scored window holds at least m 2% days. For each m,
the claim threshold (rate / 15 at its 95% lower confidence rank) and the futility threshold (2.5%, the same rank) are
calibrated on the full-period nulls (Gaussian nulls too, for claims), with windows below m counting as no verdict, then
measured on **held-out seeds**, full period and calm stress. Held-out seeds measure Monte Carlo error only: they reuse
the same 2019-26 days and prove nothing about other periods.

    python tools/v4_brier_regimes.py   # writes research/forecasts/v4_brier_regimes.{json,md}
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

SEED, SERIES = 20261015, 100_000
QUESTIONS = {"v6_abs_move_2pct_next_session": (1, 5), "v6_abs_move_2pct_within_5_sessions": (5, 10)}
SIZES, MARGIN, MIN_BASE = (125, 250), 0.02, 500
EVENT_GATES = (0, 5, 10, 15, 20)
LOOKS = {"look 1": 0.02, "look 2": 0.03}
OUT = ROOT / "research" / "forecasts" / "v4_brier_regimes"


def brier_series(horizon: int) -> dict[str, np.ndarray]:
    """d, the base rate's loss b and the 2%-day flag of each forecast day's first outcome session, from the first day
    with 500 resolved outcomes; plus the calendar of those days (exposed data)."""
    with open(ROOT / "research/data/nifty-panel/warmup_closes.csv", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["session"] == "regular" and r["date"] <= "2026-10-14"]
    returns = np.diff(np.log([float(r["underlying"]) for r in rows]))
    big = np.abs(returns) >= 0.02
    event = np.array([big[t : t + horizon].any() for t in range(len(big) - horizon + 1)])
    ewma = np.empty(len(returns))
    ewma[0] = (returns[:250] ** 2).mean()
    for t in range(1, len(returns)):
        ewma[t] = 0.94 * ewma[t - 1] + 0.06 * returns[t - 1] ** 2
    normal, out = NormalDist(), {"d": [], "b": [], "big": [], "day": []}
    for t in range(MIN_BASE + horizon, len(event)):
        model = 1 - (1 - 2 * (1 - normal.cdf(0.02 / math.sqrt(ewma[t])))) ** horizon
        rate, y = event[max(0, t - horizon - 749) : t - horizon + 1].mean(), float(event[t])
        out["d"].append((model - y) ** 2 - (rate - y) ** 2)
        out["b"].append((rate - y) ** 2)
        out["big"].append(float(big[t]))
        out["day"].append(rows[t + 1]["date"])
    return {k: np.asarray(v) for k, v in out.items()}


def calm_stretch(big: np.ndarray, length: int) -> int:
    """Start of the `length`-session stretch with the fewest 2% days (the earliest on a tie)."""
    counts = np.convolve(big, np.ones(length), "valid")
    return int(np.argmin(counts))


def sample(series: dict, d: np.ndarray, n: int, count: int, rng: np.random.Generator, stretch: tuple | None):
    """Joint circular-block resamples of (d, b, events) over the full period or inside one stretch."""
    lo, hi = stretch if stretch else (0, len(d))
    span = hi - lo
    starts = rng.integers(0, span, size=(count, math.ceil(n / study.REAL_BLOCK)))
    index = (lo + (starts[:, :, None] + np.arange(study.REAL_BLOCK)) % span).reshape(count, -1)[:, :n]
    return d[index], series["b"][index], series["big"][index].sum(axis=1)


def null_d(series: dict, flip: bool, futility: bool) -> np.ndarray:
    centred = series["d"] - series["d"].mean()
    centred = -centred if flip else centred
    return centred - MARGIN * series["b"].mean() if futility else centred


def p_claims(xd: np.ndarray, block: int) -> np.ndarray:
    return claims.batch_t_p(xd, block)


def p_futility(xd: np.ndarray, xb: np.ndarray, block: int) -> np.ndarray:
    return claims.batch_t_p(-(xd + MARGIN * xb), block)


def gated(p: np.ndarray, events: np.ndarray, gate: int) -> np.ndarray:
    return np.where(events >= gate, p, 1.0)


def threshold(p_sets: list[np.ndarray], rate: float) -> float:
    rank = claims.conservative_rank(rate, len(p_sets[0]))
    return min(float(np.sort(p)[rank]) for p in p_sets)


def _draws(series, block, n, word, futility, stretches, count: int = SERIES):
    """{name: (p, events)} for the full period and each calm stretch, both orientations."""
    out = {}
    for flip in (False, True):
        d = null_d(series, flip, futility)
        for name, stretch in [("full", None), *stretches.items()]:
            rng = np.random.default_rng(np.random.SeedSequence([SEED, word, block, n, int(flip), len(name)]))
            xd, xb, events = sample(series, d, n, count, rng, stretch)
            p = p_futility(xd, xb, block) if futility else p_claims(xd, block)
            out[f"{name} {'flipped' if flip else 'as measured'}"] = (p, events)
    return out


def gaussian_p(block: int, n: int, word: int, count: int = SERIES) -> list[np.ndarray]:
    out = []
    for i, process in enumerate(claims.GAUSSIAN):
        rng = np.random.default_rng(np.random.SeedSequence([SEED, word, block, n, 10 + i]))
        out.append(claims.batch_t_p(study.null_matrix(process, count, n, block, rng, {}), block))
    return out


def run_question(question: str, horizon: int, block: int) -> list[dict]:
    series, rows = brier_series(horizon), []
    for n in SIZES:
        stretches = {f"calm {length}": (s, s + length) for length in (125, 250)
                     for s in [calm_stretch(series["big"], length)]}  # fmt: skip
        cal_c, hold_c = _draws(series, block, n, 1, False, stretches), _draws(series, block, n, 2, False, stretches)
        cal_f, hold_f = _draws(series, block, n, 3, True, stretches), _draws(series, block, n, 4, True, stretches)
        gauss_cal, gauss_hold = gaussian_p(block, n, 5), gaussian_p(block, n, 6)
        for gate in EVENT_GATES:
            row = {"question": question, "n": n, "gate": gate, "stretches": _stretch_days(series, stretches)}
            full = [gated(p, e, gate) for k, (p, e) in cal_c.items() if k.startswith("full")]
            for look, rate in LOOKS.items():
                tau = threshold(full + gauss_cal, rate / 15) if n // block >= 12 else 0.0
                sizes = {k: float((gated(p, e, gate) <= tau).mean()) for k, (p, e) in hold_c.items()}
                sizes["gaussian"] = max(float((p <= tau).mean()) for p in gauss_hold)
                row[look] = {"claim_threshold": tau, "claim_size": sizes, "nominal": rate / 15}
            fut = [gated(p, e, gate) for k, (p, e) in cal_f.items() if k.startswith("full")]
            tau_f = threshold(fut, 0.025) if n // block >= 12 else 0.0
            row["futility_threshold"] = tau_f
            row["false_futility"] = {k: float((gated(p, e, gate) <= tau_f).mean()) for k, (p, e) in hold_f.items()}
            row["judgeable"] = {k: float((e >= gate).mean()) for k, (_, e) in hold_c.items()}
            rows.append(row)
            print(question, n, gate, flush=True)
    return rows


def _stretch_days(series: dict, stretches: dict) -> dict:
    return {k: [series["day"][lo], series["day"][hi - 1], int(series["big"][lo:hi].sum())] for k, (lo, hi) in
            stretches.items()}  # fmt: skip


def within(row: dict) -> bool:
    """Every claim size and every false-futility rate within nominal + 2 Monte Carlo SE."""
    claim_ok = all(
        size <= study.tolerance(row[look]["nominal"], SERIES)
        for look in LOOKS
        for size in row[look]["claim_size"].values()
    )
    return claim_ok and all(v <= study.tolerance(0.025, SERIES) for v in row["false_futility"].values())


def operative_thresholds(question: str, n: int, gate: int = 5) -> dict:
    """What G8 uses at a look for a Brier member with n scored outcomes: the gated claim threshold per look and the
    gated futility threshold, calibrated as in `run_question` (the calibration draws only)."""
    horizon, block = QUESTIONS[question]
    if n // block < 12:
        return {"claim": dict.fromkeys(LOOKS, 0.0), "futility": 0.0}
    series = brier_series(horizon)
    claims_cal = [gated(p, e, gate) for k, (p, e) in _draws(series, block, n, 1, False, {}).items()]
    futility_cal = [gated(p, e, gate) for k, (p, e) in _draws(series, block, n, 3, True, {}).items()]
    gauss = gaussian_p(block, n, 5)
    claim = {look: threshold(claims_cal + gauss, rate / 15) for look, rate in LOOKS.items()}
    return {"claim": claim, "futility": threshold(futility_cal, 0.025)}


def main() -> None:
    rows = [r for q, (h, b) in QUESTIONS.items() for r in run_question(q, h, b)]
    OUT.with_suffix(".json").write_text(json.dumps({"series": SERIES, "rows": rows}, indent=1) + "\n", encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(rows), encoding="utf-8")


def markdown(rows: list[dict]) -> str:
    lines = [
        "# Protocol v4: Brier rules across regimes, 2019-26 and calm stretches (`tools/v4_brier_regimes.py`)",
        "",
        f"{SERIES:,} held-out series per null; worst claim size at Holm's first step (look 1 nominal 0.133%, look 2 "
        "0.200%) and worst false-futility rate (target 2.5%) over the full-period and calm-stretch nulls in both "
        "orientations; gate m = the minimum 2% days in the scored window. Exposed data. Held-out seeds measure Monte "
        "Carlo error only, on the same days.",
        "",
        "| question | n | gate m | claim L1 | claim L2 | false futility | judgeable full, calm 125, 250 | within |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        claim = [max(r[look]["claim_size"].values()) for look in LOOKS]
        judge = [min(v for k, v in r["judgeable"].items() if k.startswith(s)) for s in ("full", "calm 125", "calm 250")]
        cells = f"{100 * claim[0]:.3f}% | {100 * claim[1]:.3f}% | {100 * max(r['false_futility'].values()):.2f}%"
        share = ", ".join(f"{100 * j:.0f}%" for j in judge)
        lines.append(
            f"| {r['question']} | {r['n']} | {r['gate']} | {cells} | {share} | {'yes' if within(r) else 'no'} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
