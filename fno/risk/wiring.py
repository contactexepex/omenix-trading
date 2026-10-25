"""Composition root of the risk manager (stories C2 and C5): the only place that picks its concrete rules, cost model,
stressed-margin method and margin age, like `fno/storage/wiring.py` for the raw data stores. A profile's `rules` list
in `config.yaml` decides which rules run; swapping a rule or method changes this file only."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..config import ROOT
from ..constants import NIFTY_SYMBOL, RISK_PROFILE_BOOKS, STRESSED_MARGIN_MULTIPLIER
from ..research_data.calendar import SessionCalendar
from ..research_engine.cycles import TradingDays
from ..research_engine.implied_vol import Black76
from .buckets import StructureBuckets
from .caps import BucketCap, NewRiskPerDay, OpenRiskCap, PaperAccountSize
from .drawdown import DrawdownBrake
from .manager import RiskManager
from .margin_age import DaysOld, MarginAge, SessionsOld
from .margins import MarginTable, MultiplierMargin, ScenarioLookupMargin, StressedMargin
from .open_risk import HeldMaxLoss, PositionRisks
from .profile_settings import ProfileSettings, all_profiles, profile_settings
from .rules import ExposureLimit, MarginRoom, MaxLossPerTrade, MaxOpenTrades, StressLoss
from .settings import RiskSettings, risk_settings
from .stress import StressEngine
from .stress_line import DailyStressLine
from .trade_costs import SimulatorTradeCosts
from .verdict import RiskRule


@dataclass(frozen=True)
class RuleParts:
    """What the rules of one profile are built from."""

    settings: RiskSettings
    profile: ProfileSettings
    costs: SimulatorTradeCosts
    engine: StressEngine
    stressed: StressedMargin
    risks: PositionRisks | None  # None when the profile runs no cap


RULES: dict[str, Callable[[RuleParts], RiskRule]] = {
    "paper_account": lambda p: PaperAccountSize(p.profile.paper_account_rs),
    "max_loss_per_trade": lambda p: MaxLossPerTrade(p.costs, p.profile.max_loss_per_trade_rs),
    "max_open_trades": lambda p: MaxOpenTrades(p.profile.max_open_trades),
    "bucket_cap": lambda p: BucketCap(p.risks, p.profile.bucket_cap_rs),
    "open_risk_cap": lambda p: OpenRiskCap(p.risks, p.profile.open_risk_cap_rs),
    "new_risk_per_day": lambda p: NewRiskPerDay(p.risks, p.profile.new_risk_per_day_rs),
    "drawdown_brake": lambda p: DrawdownBrake(p.profile.drawdown_brake_rs),
    "stress_loss": lambda p: StressLoss(p.engine, p.costs, p.settings.scenarios, p.profile.max_stress_loss_rs),
    "exposure_limit": lambda p: ExposureLimit(p.engine, p.profile.exposure),
    "margin_room": lambda p: MarginRoom(p.stressed, p.costs),
}


def _calendar() -> SessionCalendar:
    from ..storage.wiring import build_session_calendar

    return build_session_calendar()


def build_margin_age(profile: ProfileSettings, calendar: SessionCalendar | None = None) -> MarginAge:
    """The Manual profile's calendar days, or the books' trading days (A14's, on NSE's session calendar A7)."""
    if profile.margin_age_sessions is not None:
        return SessionsOld(TradingDays(calendar or _calendar()), profile.margin_age_sessions)
    return DaysOld(profile.margin_age_days)


def build_stressed_margin(settings: RiskSettings, age: MarginAge, lot_size: int) -> StressedMargin:
    """The one stressed-margin method frozen in `risk.stressed_margin`."""
    if settings.stressed_margin.method == STRESSED_MARGIN_MULTIPLIER:
        return MultiplierMargin(MarginTable(settings.margins_file, age, lot_size), settings.stressed_margin)
    names = [scenario.name for scenario in settings.scenarios]
    return ScenarioLookupMargin(settings.stressed_margin, names, age)


def build_position_risks(cfg: dict, profile: ProfileSettings) -> PositionRisks:
    """Story C5: each position's bucket and B2 maximum loss."""
    costs = SimulatorTradeCosts(cfg["charges"])
    return PositionRisks(StructureBuckets(profile.bucket_sides), HeldMaxLoss(cfg["charges"]), costs)


def build_stress_line(cfg: dict, root: Path = ROOT) -> DailyStressLine:
    """Story C5: design 6.2's daily stress line of a book, from config.yaml `risk.stress_line`."""
    risks = build_position_risks(cfg, profile_settings(cfg, RISK_PROFILE_BOOKS))
    return DailyStressLine(StressEngine(Black76()), risks, risk_settings(cfg, root).stress_line)


def build_risk_manager(
    cfg: dict, root: Path = ROOT, profile: str = RISK_PROFILE_BOOKS, calendar: SessionCalendar | None = None
) -> RiskManager:
    """Stories C2 and C5: the rules of risk profile `profile` with their settings from config.yaml `risk`, and B2's
    cost model for a trade's money."""
    settings, chosen = risk_settings(cfg, root), all_profiles(cfg)[profile]
    costs, engine = SimulatorTradeCosts(cfg["charges"]), StressEngine(Black76())
    stressed = build_stressed_margin(settings, build_margin_age(chosen, calendar), cfg["lot_sizes"][NIFTY_SYMBOL])
    risks = build_position_risks(cfg, chosen) if chosen.bucket_sides else None
    parts = RuleParts(settings, chosen, costs, engine, stressed, risks)
    rules = [RULES[name](parts) for name in chosen.rules]
    return RiskManager(rules, stressed.record(), costs)  # the same cost model prices the approved entry
