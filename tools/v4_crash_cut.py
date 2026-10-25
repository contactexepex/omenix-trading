"""Protocol v4 revisions 7-8: item E's option 2 measured (judge 98 addenda 6 and 7). A crash cut, frozen before any
v4 score and defined only on outcome-side data of the scored window, makes a crash-dominated window not judgeable (no
claim, no "no") for every member. Two candidate cuts are measured:

- `vix_above_25`: the mean closing India VIX of the window's first outcome sessions is above 25 (2019-26 mean: 17.1);
- `big_share_above_10pct`: more than 10% of the window's first outcome sessions are 2% days (2017-26 base rate 4.15%).

Cost: the share of the real rolling 2019-26 windows each cut removes, per n. Re-measurement: the same paired draws as
`v4_regime_stress.py` (same seeds, thresholds unchanged, every member gated at 5 2% days), rates among the judged
series each cut keeps, beside the same draws with no cut, each marked against **that judged set's own truth** (revision
8, judge 98 addendum 7: revision 7 marked kept series against the whole stretch's truth). Full period and busy
stretches only: calm stretches hold no judgeable window.

    python tools/v4_crash_cut.py   # writes research/forecasts/v4_crash_cut.{json,md}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_regime_stress as stress  # noqa: E402

CUTS = {
    "vix_above_25": lambda vix, big: vix > 25,
    "big_share_above_10pct": lambda vix, big: big > 0.10,
}
STRETCHES = ("full", "busy 125", "busy 250")
OUT = stress.FORECASTS / "v4_crash_cut"


def window_means(series: dict, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Mean VIX and 2%-day share of every real rolling n-session window."""
    ones = np.ones(n) / n
    return np.convolve(series["vix"], ones, "valid"), np.convolve(series["big"], ones, "valid")


def cost(question: str) -> list[dict]:
    series, rows = stress.member_series(question), []
    for n in stress.SIZES:
        vix, big = window_means(series, n)
        gate = big * n >= stress.MIN_EVENT_DAYS - 1e-9  # revision 8: every member
        for name, cut in CUTS.items():
            out = cut(vix, big)
            rows.append({"question": question, "n": n, "cut": name, "removed": float(out.mean()),
                         "judgeable_before": float(gate.mean()), "judgeable_after": float((gate & ~out).mean()),
                         "removed_days": [str(series["day"][i]) for i in np.where(out)[0][[0, -1]]] if out.any()
                         else []})  # fmt: skip
    return rows


def remeasure(question: str) -> list[dict]:
    series, rows = stress.member_series(question), []
    margin = stress.QUESTIONS[question][3]
    cuts = {"no cut": lambda vix, big: np.zeros(len(vix), bool), **CUTS}
    for name, stretch in stress.stretches(series["big"]).items():
        if name not in STRETCHES:
            continue
        for n in stress.SIZES:
            for futility in (False, True):
                for flip in (False, True):
                    d, index = stress.draw(question, series, name, stretch, n, flip, futility)
                    vix, big = series["vix"][index].mean(axis=1), series["big"][index].mean(axis=1)
                    for cut_name, cut in cuts.items():
                        result = stress.verdict_rates(question, n, d, series, index, futility, ~cut(vix, big))
                        rows.append({"question": question, "n": n, "stretch": name, "cut": cut_name, "margin": margin,
                                     "kind": "futility" if futility else "claim",
                                     "orientation": "flipped" if flip else "as measured", **result})  # fmt: skip
                    print(question, n, name, futility, flip, flush=True)
    return rows


def markdown(costs: list[dict], rows: list[dict]) -> str:
    lines = [
        "# Protocol v4: item E option 2, crash cuts measured (`tools/v4_crash_cut.py`)",
        "",
        "## Cost: real rolling 2019-26 windows removed",
        "",
        "Judgeable = at least 5 2% days (revision 8: every member).",
        "",
        "| question | n | cut | removed | judgeable before | judgeable after | removed windows start |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in costs:
        span = " to ".join(c["removed_days"])
        lines.append(f"| {c['question']} | {c['n']} | {c['cut']} | {100 * c['removed']:.1f}% | "
                     f"{100 * c['judgeable_before']:.0f}% | {100 * c['judgeable_after']:.0f}% | {span} |")  # fmt: skip
    lines += [
        "",
        "## Re-measured on each judged set's own truth (paired draws with `v4_regime_stress.md`)",
        "",
        "Rates among the judged series that each cut keeps (5+ 2% days and not cut), next to the same draws with no"
        ' cut. **set** = that judged set\'s own pooled true improvement: a "no" is false only where set >= the minimum'
        " effect, a claim only where set <= 0. **Bold**: false and above nominal + 2 Monte Carlo SE of the judged"
        " count; *italic*: above it but that set's truth. A set with almost nothing judged says little.",
        "",
        "| question | stretch | n | orientation | cut | judged | claim | futility | set claim / futility null |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    keyed = {(r["question"], r["stretch"], r["n"], r["orientation"], r["cut"], r["kind"]): r for r in rows}
    for (q, s, n, o, cut, kind), c in keyed.items():
        if kind != "claim":
            continue
        f = keyed[(q, s, n, o, cut, "futility")]
        claim = _mark(c["conditional"], c["set_truth"] is not None and c["set_truth"] > 0, stress.CLAIM_NOMINAL, c)
        futility = _mark(f["conditional"], f["set_truth"] is None or f["set_truth"] < f["margin"], 0.025, f)
        lines.append(f"| {q} | {s} | {n} | {o} | {cut} | {100 * f['judged']:.1f}% | {claim} | {futility} | "
                     f"{_estimate(c['set_truth'])} / {_estimate(f['set_truth'])} |")  # fmt: skip
    return "\n".join(lines) + "\n"


def _estimate(value: float | None) -> str:
    return "none" if value is None else f"{value:+.3f}"


def _mark(rate: float, set_truth: bool, nominal: float, row: dict) -> str:
    text = f"{100 * rate:.2f}%"
    if rate <= stress.study.tolerance(nominal, max(1, round(row["judged"] * stress.SERIES))):
        return text
    return f"*{text}*" if set_truth else f"**{text}**"


def main() -> None:
    costs = [c for q in stress.QUESTIONS for c in cost(q)]
    rows = [r for q in stress.QUESTIONS for r in remeasure(q)]
    OUT.with_suffix(".json").write_text(json.dumps({"cost": costs, "rows": rows}, indent=1) + "\n", encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(costs, rows), encoding="utf-8")


if __name__ == "__main__":
    main()
