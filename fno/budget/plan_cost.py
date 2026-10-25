"""The Claude plan's monthly cost (story F8; owner, 15 Oct 2026: "Claude plan cost: INR 20,000 a month"). The decided
figure applies to every month from its first month until a newer decision changes the one config value that cites it,
so nobody adds a row by hand each month. A payment row the owner records for a month (`operating_costs.csv`, item
`Claude subscription`) is that month's cash spend; when it differs from the decided figure the meter says so. The
allocation uses the recorded payment when there is one, else the decided figure; before the first month, neither."""

from __future__ import annotations

from dataclasses import dataclass

from .items import DECISION_ROW, cited_row

NO_DECISION = "budget.plan_cost.decision {cite!r} is not a row of docs/DESK_DECISIONS.md: the decided cost is not used"
DIFFERS = "{month}: recorded Claude payment Rs {paid:,.2f} differs from the decided Rs {decided:,.2f} a month"
DECIDED_LABEL = "decided monthly fee ({cite}); no payment row recorded"


@dataclass(frozen=True)
class DecidedPlanCost:
    rs_per_month: float
    from_month: str  # YYYY-MM
    decision: str  # `DESK_DECISIONS <date>: <bold title>`

    @classmethod
    def from_config(cls, plan: dict | None, decisions: str) -> DecidedPlanCost | None:
        if not plan:
            return None
        decided = cls(float(plan["rs_per_month"]), str(plan["from_month"]), str(plan["decision"]))
        if decided.rs_per_month < 0 or cited_row(decided.decision) not in set(DECISION_ROW.findall(decisions)):
            raise ValueError(NO_DECISION.format(cite=decided.decision))
        return decided

    def for_month(self, month: str) -> float | None:
        return self.rs_per_month if month >= self.from_month else None


@dataclass(frozen=True)
class PlanCost:
    allocated_from_rs: float | None  # what the allocation splits; None: unknown
    cash_line: str  # how the meter shows the month's cash spend for the plan
    warning: str = ""


def month_plan_cost(recorded_rs: float | None, decided: DecidedPlanCost | None, month: str) -> PlanCost:
    figure = decided.for_month(month) if decided else None
    if recorded_rs is not None:
        differs = figure is not None and abs(recorded_rs - figure) >= 0.005
        warning = DIFFERS.format(month=month, paid=recorded_rs, decided=figure) if differs else ""
        return PlanCost(recorded_rs, f"Rs {recorded_rs:,.2f}", warning)
    if figure is not None:
        return PlanCost(figure, f"Rs {figure:,.2f} " + f"({DECIDED_LABEL.format(cite=decided.decision)})")
    return PlanCost(None, "not recorded")
