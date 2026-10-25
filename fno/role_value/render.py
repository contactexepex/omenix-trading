"""The role-value report as Markdown (story F9a): one row per unit, the risk effects beside the verdict, the open and
excluded pairs, the control roles, and the honest limits every report repeats."""

from __future__ import annotations

from .cost import COST_LABEL
from .report import RoleValueResult
from .score import UnitScore

PROVISIONAL_NOTE = (
    "Every verdict is provisional: none is evidence until F9b's end-to-end card-withholding test "
    "passes; the bootstrap's coverage on sparse ablations is unvalidated (review 124)."
)
NO_ROWS = "no paired decisions yet: books 2-3 have not traded with shadow decisions (F9b, slice E)."
SLOW = ("Each unit is ablated once every n decision days (n units), so 30 changed opportunities can take years; "
        "no early figure is an answer.")  # fmt: skip
COLUMNS = ("Unit", "Applicable", "Changed", "Mean difference (Rs)", "Cost on scored dates (Rs)", "Net value (Rs)",
           "Interval 5-95% (shown only)", "p earns", "p drop", "Verdict", "Worst month (Rs)",
           "Max-loss difference (Rs)", "Operating cost, all consulted days (Rs)")  # fmt: skip
HEADER = "| " + " | ".join(COLUMNS) + " |"


def _rs(value) -> str:
    return "unknown" if value is None else f"{value:,.2f}"


def _p(value) -> str:
    return "-" if value is None else f"{value:.4f}"


def _row(score: UnitScore, verdict: str) -> str:
    interval = "-" if score.interval is None else f"{score.interval[0]:,.2f} to {score.interval[1]:,.2f}"
    month = "-" if score.worst_month is None else f"{score.worst_month[0]}: {score.worst_month[1]:,.2f}"
    mean = "-" if score.mean_difference is None else f"{score.mean_difference:,.2f}"
    risk = "-" if score.mean_max_loss_difference is None else f"{score.mean_max_loss_difference:,.2f}"
    cells = [score.unit, str(score.applicable), str(score.changed), mean, _rs(score.cost), _rs(score.mean_net_value),
             interval, _p(score.p_earns), _p(score.p_drop), verdict, month, risk,
             _rs(score.operating_cost)]  # fmt: skip
    return "| " + " | ".join(cells) + " |"


def _spread(score: UnitScore) -> str:
    blocks = "; ".join(f"{first} to {last}" for first, last in score.block_spans)
    months = ", ".join(f"{month}: {n}" for month, n in score.months)
    return f"- {score.unit}: blocks of 20 observations {blocks}; observations by month {months}"


def render(result: RoleValueResult) -> str:
    p = result.period
    head = f"Protocol: {result.protocol}. Common start: {p.common_start}. Cost: {COST_LABEL}."
    lines = [
        f"# Role value: {p.book}, {p.first} to {p.last}",
        "",
        head + " Risk columns are shown, never deciding.",
        "",
    ]
    if not result.rows:
        return "\n".join(lines + [NO_ROWS, "", SLOW, ""])
    lines += [HEADER, "|" + " --- |" * len(COLUMNS)]
    lines += [_row(s, result.verdicts.get(s.unit, "")) for s in result.scores]
    lines += ["", PROVISIONAL_NOTE, SLOW, "", "## Sample spread (beside the p-values)", ""]
    lines += [_spread(s) for s in result.scores if s.applicable]
    lines += ["", f"## Open pairs: {len(result.open_pairs)} (waiting, never scored as 0)", ""]
    lines += [f"- {line}" for line in result.open_pairs] or ["- none"]
    lines += ["", "## Rows not scored", ""]
    lines += [f"- {reason}: {n}" for reason, n in sorted(result.excluded.items())] or ["- none"]
    if result.controls:
        c = result.controls
        lines += ["", "## Control roles (never ablated; no profit figure)", "",
                  f"- caught violations (failed C4 checks): {c.caught_violations}",
                  f"- prevented invalid actions (blocked day and opportunity): {c.prevented_actions}"]  # fmt: skip
        lines += [f"  - {check}: {n}" for check, n in c.by_check.items()]
    return "\n".join(lines + [""])
