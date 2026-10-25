"""Each gate's own figures as the gate log's `numbers` text (k=v;k=v), and the lines the commands print."""

from __future__ import annotations

from .cost_wall import ASSUMED_HURDLE, NO_STATED_EDGE, Screen
from .data_spend import SpendVerdict
from .sample_plan import SamplePlan

_REASON_KEYS = {NO_STATED_EDGE: "reason=no_stated_edge", ASSUMED_HURDLE: "assumed_hurdle=yes"}


def _rupees(value: float) -> str:
    return f"{value:.1f}"


def screen_numbers(result: Screen) -> str:
    if not result.figures:
        return ";".join(_REASON_KEYS[reason] for reason in result.reasons)
    f = result.figures
    pairs = [f"bound={_rupees(f['bound'])}", f"expected={_rupees(f['expected'])}", f"cost={_rupees(f['cost'])}",
             f"tail={_rupees(f['tail'])}", f"net={_rupees(f['net'])}", f"ratio={f['ratio']:.2f}",
             f"thin_margin={'yes' if result.thin_margin else 'no'}"]  # fmt: skip
    return ";".join(pairs)


def screen_lines(idea_id: str, result: Screen) -> list[str]:
    head = f"{idea_id}: G1 {result.outcome}"
    if not result.figures:
        return [f"{head} ({'; '.join(result.reasons)})"]
    f = result.figures
    warning = (
        f"; thin margin (gross / cost {f['ratio']:.2f}, below 2: a warning, never a pass mark)" * result.thin_margin
    )
    return [
        f"{head}: expected net {f['net']:+,.1f} a trade on the conservative bound",
        f"  bound {f['bound']:+,.1f} - cost {f['cost']:,.1f} - tail beyond the gross {f['tail']:,.1f}{warning}",
    ]


def spend_numbers(verdict: SpendVerdict) -> str:
    return f"rows={len(verdict.rows)};not_fresh={len(verdict.not_fresh)}"


def spend_lines(idea_id: str, verdict: SpendVerdict) -> list[str]:
    rows = [f"  {row.status}: {row.key}" for row in verdict.rows]
    return [f"{idea_id}: G2 {verdict.outcome} (rows read from research/DATA_SPEND.md)", *rows]


def plan_numbers(plan: SamplePlan) -> str:
    return f"z={plan.z:.4f};n={plan.n};years={plan.years:.2f}"


def plan_lines(idea_id: str, plan: SamplePlan) -> list[str]:
    return [f"{idea_id}: G3 {plan.outcome}: n = {plan.n} trades (z {plan.z:.3f}), about {plan.years:.1f} years"]
