"""Protocol v4 revision 5: Brier thresholds by event-count band (judge 98 addendum 4).

Revision 4's single Brier threshold per question averaged over calm and busy windows, yet a window's count of 2% days
is known before the verdict. Windows with 5-7 such days then over-rejected 2-4x. Here each band of the count (5-7,
8-12, 13 or more) gets its own claim and futility thresholds, calibrated on the 2019-26 nulls (`v4_brier_regimes.py`)
**conditioned to that band** (the rate among the band's series), and is measured on held-out seeds the same way.
Gaussian nulls have no events and stay in every band's claim calibration. Held-out seeds measure Monte Carlo error
only, on the same 2019-26 days.

    python tools/v4_brier_bands.py   # writes research/forecasts/v4_brier_bands.{json,md}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import v4_brier_regimes as regimes  # noqa: E402
import v4_claim_thresholds as claims  # noqa: E402
import v4_size_study as study  # noqa: E402

SERIES = 200_000
BANDS = ((5, 7), (8, 12), (13, None))
OUT = ROOT / "research" / "forecasts" / "v4_brier_bands"


def band_name(band) -> str:
    lo, hi = band
    return f"{lo}-{hi}" if hi is not None else f"{lo}+"


def in_band(events: np.ndarray, band: tuple[int, int | None]) -> np.ndarray:
    lo, hi = band
    return (events >= lo) & (events <= hi if hi is not None else True)


def band_threshold(p_sets: list[tuple[np.ndarray, np.ndarray]], band, rate: float) -> float:
    """The smallest conservative conditional quantile over the sets; `p_sets` are (p, events or None for Gaussian)."""
    out = []
    for p, events in p_sets:
        chosen = p if events is None else p[in_band(events, band)]
        if len(chosen):
            out.append(float(np.sort(chosen)[claims.conservative_rank(rate, len(chosen))]))
    return min(out)


def band_rates(p_sets, band, tau: float) -> dict[str, tuple[float, int]]:
    """Conditional rejection rate and series count in the band, per held-out null."""
    out = {}
    for name, (p, events) in p_sets.items():
        chosen = p if events is None else p[in_band(events, band)]
        out[name] = (float((chosen <= tau).mean()) if len(chosen) else 0.0, len(chosen))
    return out


def run_question(question: str) -> list[dict]:
    horizon, block = regimes.QUESTIONS[question]
    series, rows = regimes.brier_series(horizon), []
    for n in regimes.SIZES:
        cal_c = regimes._draws(series, block, n, 11, False, {}, SERIES)
        hold_c = regimes._draws(series, block, n, 12, False, {}, SERIES)
        cal_f = regimes._draws(series, block, n, 13, True, {}, SERIES)
        hold_f = regimes._draws(series, block, n, 14, True, {}, SERIES)
        gauss_cal = [(p, None) for p in regimes.gaussian_p(block, n, 15, SERIES)]
        gauss_hold = {f"gaussian {i}": (p, None) for i, p in enumerate(regimes.gaussian_p(block, n, 16, SERIES))}
        share = float(np.mean([(e >= regimes.EVENT_GATES[1]).mean() for _, e in hold_c.values()]))
        for band in BANDS:
            row = {"question": question, "n": n, "band": list(band), "judgeable_share_all": share}
            row["band_share"] = float(np.mean([in_band(e, band).mean() for _, e in hold_c.values()]))
            for look, rate in regimes.LOOKS.items():
                tau = band_threshold(list(cal_c.values()) + gauss_cal, band, rate / 15)
                claim = band_rates({**hold_c, **gauss_hold}, band, tau)
                row[look] = {"nominal": rate / 15, "claim_threshold": tau, "claim": claim}
                row[look] |= {
                    "outcomes_r3": claims.outcomes_needed(tau, 3),
                    "outcomes_r5": claims.outcomes_needed(tau, 5),
                }
            tau_f = band_threshold(list(cal_f.values()), band, 0.025)
            row["futility_threshold"] = tau_f
            row["futility"] = band_rates(hold_f, band, tau_f)
            rows.append(row)
            print(question, n, band, flush=True)
    return rows


def within(row: dict) -> bool:
    claim_ok = all(rate <= study.tolerance(row[look]["nominal"], count)
                   for look in regimes.LOOKS for rate, count in row[look]["claim"].values() if count)  # fmt: skip
    return claim_ok and all(rate <= study.tolerance(0.025, count) for rate, count in row["futility"].values() if count)


def markdown(rows: list[dict]) -> str:
    lines = [
        "# Protocol v4: Brier thresholds by event-count band (`tools/v4_brier_bands.py`)",
        "",
        f"{SERIES:,} series per null (calibration and held-out); rates are conditional on the band; worst held-out "
        "claim size at Holm's first step (L1 nominal 0.133%, L2 0.200%) and worst false futility (target 2.5%), "
        "against nominal + 2 Monte Carlo SE for the band's count. Exposed 2019-26 data; held-out seeds measure "
        "Monte Carlo error only.",
        "",
        "| question | n | 2% days | share of windows | claim L1 | claim L2 | false futility | L1 threshold | "
        "outcomes r=3 / 5 | within |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        band = band_name(r["band"])
        claim = [max(rate for rate, _ in r[look]["claim"].values()) for look in regimes.LOOKS]
        futility = max(rate for rate, _ in r["futility"].values())
        need = f"{r['look 1']['outcomes_r3']} / {r['look 1']['outcomes_r5']}"
        lines.append(
            f"| {r['question']} | {r['n']} | {band} | {100 * r['band_share']:.0f}% | {100 * claim[0]:.3f}% | "
            f"{100 * claim[1]:.3f}% | {100 * futility:.2f}% | {r['look 1']['claim_threshold']:.3g} | {need} | "
            f"{'yes' if within(r) else '**no**'} |"
        )
    return "\n".join(lines) + "\n"


def operative_thresholds(question: str, n: int, band: tuple[int, int | None]) -> dict:
    """What G8 uses at a look for a Brier member with n scored outcomes in a band: the band's claim threshold per look
    and its futility threshold (the calibration draws only)."""
    horizon, block = regimes.QUESTIONS[question]
    series = regimes.brier_series(horizon)
    cal_c = list(regimes._draws(series, block, n, 11, False, {}, SERIES).values())
    cal_f = list(regimes._draws(series, block, n, 13, True, {}, SERIES).values())
    gauss = [(p, None) for p in regimes.gaussian_p(block, n, 15, SERIES)]
    claim = {look: band_threshold(cal_c + gauss, band, rate / 15) for look, rate in regimes.LOOKS.items()}
    return {"claim": claim, "futility": band_threshold(cal_f, band, 0.025)}


def busy_stress() -> list[dict]:
    """Revision 6 disclosure: V6b's banded thresholds applied to series resampled inside the busiest 125 and 250
    sessions (most 2% days, the 2020 crash), both orientations, claims (look 1) and futility, per band."""
    question = "v6_abs_move_2pct_within_5_sessions"
    horizon, block = regimes.QUESTIONS[question]
    series, data = regimes.brier_series(horizon), json.loads(OUT.with_suffix(".json").read_text(encoding="utf-8"))
    rows = []
    for n in regimes.SIZES:
        fixed = {tuple(r["band"]): r for r in data["rows"] if r["question"] == question and r["n"] == n}
        for length in (125, 250):
            counts = np.convolve(series["big"], np.ones(length), "valid")
            start = int(np.argmax(counts))
            for futility in (False, True):
                for flip in (False, True):
                    rng = np.random.default_rng(np.random.SeedSequence([regimes.SEED, 77, n, length, flip, futility]))
                    d = regimes.null_d(series, flip, futility)
                    xd, xb, events = regimes.sample(series, d, n, SERIES, rng, (start, start + length))
                    p = regimes.p_futility(xd, xb, block) if futility else regimes.p_claims(xd, block)
                    for band, r in fixed.items():
                        chosen = in_band(events, band)
                        tau = r["futility_threshold"] if futility else r["look 1"]["claim_threshold"]
                        if chosen.sum() >= 1_000:
                            rows.append({"n": n, "stretch": [series["day"][start], series["day"][start + length - 1]],
                                         "kind": "futility" if futility else "claim", "flipped": flip,
                                         "band": band_name(band), "count": int(chosen.sum()),
                                         "rate": float((p[chosen] <= tau).mean())})  # fmt: skip
    return rows


def main() -> None:
    rows = [r for q in regimes.QUESTIONS for r in run_question(q)]
    OUT.with_suffix(".json").write_text(json.dumps({"series": SERIES, "rows": rows}, indent=1) + "\n", encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(rows), encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:] == ["--busy-stress"]:
        rows = busy_stress()
        path = ROOT / "research" / "forecasts" / "v4_brier_busy_stress.json"
        path.write_text(json.dumps({"series": SERIES, "rows": rows}, indent=1) + "\n", encoding="utf-8")
    else:
        main()
