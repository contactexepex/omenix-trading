"""Protocol v4 revision 6: a V7-specific null (ChatGPT review 101). V7 asks P(VIX(d+5) > VIX(d)).

The null pairs, for every exposed regular session with a valid base rate (at least 500 resolved outcomes), the Brier
difference between a rival forecaster and the 750-session base rate with the base rate's own loss. The rival is a
two-cell conditional base rate: the share of "VIX higher in 5 sessions" among the last 750 resolved days whose VIX was
on the same side of its 20-session mean as today (point in time; the plain base rate stands in when a cell has fewer
than 100 days). Series are resampled jointly in circular 20-session blocks, both orientations, over the full period
and inside the calmest and the most volatile 125- and 250-session stretches (lowest and highest mean VIX). Rules:

- R0, borrowed: V6b's NIFTY 2%-day gate and banded thresholds (`v4_brier_bands.json`), applied to V7.
- R1, own: V7's thresholds calibrated on its full-period nulls (and Gaussian nulls for claims), no gate.
- R2, own, banded by the window's mean VIX (below 13, 13-17, above 17), each band calibrated on its own conditioned
  nulls.

Held-out seeds measure Monte Carlo error only, on the same 2019-26 days. Exposed data.

    python tools/v4_vix_null.py   # writes research/forecasts/v4_vix_null.{json,md}
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import v4_brier_bands as bands  # noqa: E402
import v4_brier_regimes as regimes  # noqa: E402
import v4_claim_thresholds as claims  # noqa: E402
import v4_size_study as study  # noqa: E402

SEED, SERIES, HORIZON, BLOCK, MARGIN = 20261015, 200_000, 5, 10, 0.02
VIX_BANDS = ((0.0, 13.0), (13.0, 17.0), (17.0, math.inf))
MIN_CELL = 100
LOOKS = regimes.LOOKS
OUT = ROOT / "research" / "forecasts" / "v4_vix_null"


def vix_series() -> dict[str, np.ndarray]:
    with open(ROOT / "research/data/nifty-panel/warmup_closes.csv", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["session"] == "regular" and r["date"] <= "2026-10-14"]
    vix = np.array([float(r["vix"]) for r in rows])
    returns = np.diff(np.log([float(r["underlying"]) for r in rows]))
    up = vix[HORIZON:] > vix[:-HORIZON]  # outcome of day t, known at t + 5
    mean20 = np.array([vix[max(0, t - 19) : t + 1].mean() for t in range(len(vix))])
    below = vix < mean20
    out = {"d": [], "b": [], "big": [], "vix": [], "day": []}
    for t in range(regimes.MIN_BASE + HORIZON, len(up)):
        past = slice(max(0, t - HORIZON - 749), t - HORIZON + 1)
        base, y = up[past].mean(), float(up[t])
        cell = up[past][below[past] == below[t]]
        rival = cell.mean() if len(cell) >= MIN_CELL else base
        out["d"].append((rival - y) ** 2 - (base - y) ** 2)
        out["b"].append((base - y) ** 2)
        out["big"].append(float(abs(returns[t]) >= 0.02))  # the NIFTY 2%-day flag of session t + 1
        out["vix"].append(vix[t])
        out["day"].append(rows[t]["date"])
    return {k: np.asarray(v) for k, v in out.items()}


def stretch(vix: np.ndarray, length: int, calmest: bool) -> tuple[int, int]:
    means = np.convolve(vix, np.ones(length) / length, "valid")
    start = int(np.argmin(means) if calmest else np.argmax(means))
    return start, start + length


def draws(series: dict, n: int, word: int, futility: bool, regions: dict) -> dict:
    """{name: (p, NIFTY 2% days, mean VIX)} per region and orientation, `SERIES` joint block resamples each."""
    out = {}
    for flip in (False, True):
        centred = series["d"] - series["d"].mean()
        d = (-centred if flip else centred) - (MARGIN * series["b"].mean() if futility else 0.0)
        for number, (name, (lo, hi)) in enumerate(regions.items()):
            rng = np.random.default_rng(np.random.SeedSequence([SEED, word, n, int(flip), number]))
            starts = rng.integers(0, hi - lo, size=(SERIES, math.ceil(n / study.REAL_BLOCK)))
            index = (lo + (starts[:, :, None] + np.arange(study.REAL_BLOCK)) % (hi - lo)).reshape(SERIES, -1)[:, :n]
            xd, xb = d[index], series["b"][index]
            p = claims.batch_t_p(-(xd + MARGIN * xb), BLOCK) if futility else claims.batch_t_p(xd, BLOCK)
            out[f"{name} {'flipped' if flip else 'as measured'}"] = (
                p,
                series["big"][index].sum(1),
                series["vix"][index].mean(1),
            )
    return out


def in_vix_band(mean_vix: np.ndarray, band: tuple[float, float]) -> np.ndarray:
    return (mean_vix >= band[0]) & (mean_vix < band[1])


def conditional_threshold(sets: list[np.ndarray], rate: float) -> float:
    """Smallest conservative quantile over the sets (each already restricted to its eligible series)."""
    return min(float(np.sort(p)[claims.conservative_rank(rate, len(p))]) for p in sets if len(p))


def per_null(held: dict, select, tau) -> dict[str, tuple[float, int]]:
    """Conditional rejection rate and eligible count for each held-out null (region and orientation)."""
    out = {}
    for name, (p, big, vix) in held.items():
        m = select(big, vix)
        if m.any():
            out[name] = (float((p[m] <= tau).mean()), int(m.sum()))
    return out


def worst(held: dict, select, tau) -> tuple[float, int]:
    """Worst conditional rejection rate over the held-out nulls, with that null's eligible count."""
    return max(per_null(held, select, tau).values(), default=(0.0, 0))


def cell_rows(series: dict, n: int, borrowed: dict) -> list[dict]:
    regions = {"full": (0, len(series["d"]))}
    for length in (125, 250):
        regions[f"calm {length}"] = stretch(series["vix"], length, True)
        regions[f"volatile {length}"] = stretch(series["vix"], length, False)
    full = {"full": regions["full"]}
    cal_c, hold_c = draws(series, n, 21, False, full), draws(series, n, 22, False, regions)
    cal_f, hold_f = draws(series, n, 23, True, full), draws(series, n, 24, True, regions)
    gauss = regimes.gaussian_p(BLOCK, n, 25, SERIES)
    every = lambda big, vix: np.ones(len(big), bool)  # noqa: E731
    rows = []
    rules = [("R0 borrowed V6b, NIFTY band " + bands.band_name(b), lambda big, vix, b=b: bands.in_band(big, b),
              borrowed[tuple(b)]) for b in bands.BANDS]  # fmt: skip
    rules.append(("R1 own, no gate", every, None))
    rules += [(f"R2 own, mean VIX {lo:g}-{hi:g}", lambda big, vix, b=(lo, hi): in_vix_band(vix, b), None)
              for lo, hi in VIX_BANDS]  # fmt: skip
    for name, select, fixed in rules:
        row = {"n": n, "rule": name}
        for look, rate in LOOKS.items():
            tau = fixed["claim"][look] if fixed else conditional_threshold(
                [p[select(big, vix)] for p, big, vix in cal_c.values()] + gauss, rate / 15)  # fmt: skip
            size, count = worst(hold_c, select, tau)
            row[look] = {"threshold": tau, "size": size, "count": count, "nominal": rate / 15}
            row[look]["by_null"] = per_null(hold_c, select, tau)
        tau_f = fixed["futility"] if fixed else conditional_threshold(
            [p[select(big, vix)] for p, big, vix in cal_f.values()], 0.025)  # fmt: skip
        size, count = worst(hold_f, select, tau_f)
        row["futility"] = {"threshold": tau_f, "rate": size, "count": count, "by_null": per_null(hold_f, select, tau_f)}
        row["share"] = float(np.mean([select(big, vix).mean() for _, big, vix in hold_c.values()]))
        rows.append(row)
        print(n, name, flush=True)
    return rows


def borrowed_thresholds(n: int) -> dict:
    data = json.loads((ROOT / "research/forecasts/v4_brier_bands.json").read_text(encoding="utf-8"))
    rows = [r for r in data["rows"] if r["question"] == "v6_abs_move_2pct_within_5_sessions" and r["n"] == n]
    return {tuple(r["band"]): {"claim": {look: r[look]["claim_threshold"] for look in LOOKS},
                               "futility": r["futility_threshold"]} for r in rows}  # fmt: skip


def within(row: dict) -> bool:
    claim = all(
        row[look]["size"] <= study.tolerance(row[look]["nominal"], max(row[look]["count"], 1)) for look in LOOKS
    )
    return claim and row["futility"]["rate"] <= study.tolerance(0.025, max(row["futility"]["count"], 1))


def markdown(rows: list[dict]) -> str:
    lines = [
        "# Protocol v4: V7's own null (`tools/v4_vix_null.py`)",
        "",
        f"{SERIES:,} series per null; worst held-out conditional rate over the full period and the calmest and most "
        "volatile 125/250-session stretches, both orientations. Claim nominal 0.133% (L1), 0.200% (L2); futility "
        "target 2.5%. Exposed 2019-26 data; held-out seeds measure Monte Carlo error only.",
        "",
        "| n | rule | share of windows | claim L1 | claim L2 | false futility | within |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['n']} | {r['rule']} | {100 * r['share']:.0f}% | {100 * r['look 1']['size']:.3f}% | "
                     f"{100 * r['look 2']['size']:.3f}% | {100 * r['futility']['rate']:.2f}% | "
                     f"{'yes' if within(r) else '**no**'} |")  # fmt: skip
    return "\n".join(lines) + "\n"


def main() -> None:
    series = vix_series()
    rows = [r for n in regimes.SIZES for r in cell_rows(series, n, borrowed_thresholds(n))]
    OUT.with_suffix(".json").write_text(json.dumps({"series": SERIES, "rows": rows}, indent=1) + "\n", encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(rows), encoding="utf-8")


if __name__ == "__main__":
    main()
