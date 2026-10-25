"""Composition root of the AI usage ledger and the budget meter (stories F8 and BG1): the only place that picks the
concrete usage readers, files, session calendar and alert sender. The alert sender is a dry run in this story; a later
routine swaps in the Slack sender here (one line)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..accounting.ledgers import read_operating_costs
from ..alerts.dry_run import DryRunAlertSender
from ..alerts.sender import AlertSender
from ..config import ROOT, load_app_config
from ..storage.wiring import build_session_calendar
from .allocation import allocate, coverage_warnings
from .cap import CapSettings, Coverage, cap_reading
from .capture_coverage import not_captured
from .items import month_items, plan_cost, unapproved_costs, unknown_items
from .plan_cost import DecidedPlanCost, month_plan_cost
from .report import MonthMeter
from .routine_coverage import DataRoutine, routine_gap
from .self_timed import SelfTimedUsageReader
from .session_roster import SessionRoster, development_coverage
from .stop_rule_tracker import ReviewDate, review_date
from .usage_export import ExportFileUsageReader
from .usage_ledger import UsageLedger
from .usage_reader import SessionUsageReader

COSTS_FILE = "accounting/operating_costs.csv"
DECISIONS_FILE = "docs/DESK_DECISIONS.md"


def build_usage_reader(path: Path, self_timed: bool = False) -> SessionUsageReader:
    return SelfTimedUsageReader(path) if self_timed else ExportFileUsageReader(path)


def build_usage_ledger(root: Path = ROOT) -> UsageLedger:
    return UsageLedger(root)


def build_session_roster(root: Path = ROOT) -> SessionRoster:
    return SessionRoster(root)


def build_data_routine_names(config: dict | None = None) -> list[str]:
    return [r.name for r in DataRoutine.from_config((config or load_app_config())["budget"].get("data_routines"))]


def build_budget_alert_sender() -> AlertSender:
    return DryRunAlertSender()


def build_month_meter(month: str, today: date, root: Path = ROOT, config: dict | None = None) -> MonthMeter:
    budget, decisions = (config or load_app_config())["budget"], _text(root / DECISIONS_FILE)
    costs = read_operating_costs(_text(root / COSTS_FILE)) if (root / COSTS_FILE).is_file() else []
    usage = [row for row in UsageLedger(root).rows() if row["date"].startswith(month)]
    missing = not_captured(root, month, usage, today.isoformat())
    development = development_coverage(SessionRoster(root).rows(), usage, month, today)
    routines = routine_gap(DataRoutine.from_config(budget.get("data_routines")), usage, month, today)
    coverage = Coverage(len(missing), development.reason, routines)
    plan = month_plan_cost(
        plan_cost(costs, month), DecidedPlanCost.from_config(budget.get("plan_cost"), decisions), month
    )
    return MonthMeter(
        month=month,
        items=month_items(costs, month),
        allocation=allocate(month, plan.allocated_from_rs, usage),
        cap=cap_reading(usage, CapSettings.from_config(budget), month, coverage),
        usage_rows=usage,
        missing_captures=missing,
        needs_owner_yes=unapproved_costs(costs, month, decisions) + ([plan.warning] if plan.warning else []),
        unknown_items=unknown_items(costs, month),
        allocation_warnings=coverage_warnings(len(missing), development.reason, routines),
        development_gap=development.reason,
        routine_gap=routines,
        plan_cash=plan.cash_line,
    )


def build_review_date(config: dict | None = None) -> ReviewDate:
    rule = (config or load_app_config())["budget"]["stop_rule"]
    freeze = date.fromisoformat(rule["v4_freeze_date"]) if rule.get("v4_freeze_date") else None
    return review_date(freeze, rule["projected_v4_freeze_month"], build_session_calendar())


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""
