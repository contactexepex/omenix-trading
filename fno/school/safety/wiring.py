"""Composition root of `fno/school/safety/` (story MS-P1d): the safety laws of story 3.3 for one slot, in a fixed
order, with the school's own limits (`school` block) and C2's rule classes, cost model and stressed margin (the books
profile's bucket sides). Built per slot: C2's caps mark positions held on other
roads at their own road's snapshot of the same slot. Margin room reads MS-P1m's margin per trade, built once per run
(`build_margin`) and passed in."""

from collections.abc import Mapping

from ...constants import RISK_PROFILE_BOOKS
from ...nse_margins.road_wiring import build_road_margin
from ...risk.caps import BucketCap, NewRiskPerDay, OpenRiskCap
from ...risk.margins import StressedMargin
from ...risk.open_risk import HeldMaxLoss, PositionRisks
from ...risk.profile_settings import profile_settings
from ...risk.rules import MaxLossPerTrade
from ...risk.trade_costs import SimulatorTradeCosts
from ..constants import RefusalReason, RoadCode
from ..contracts.snapshot import SlotSnapshot
from ..execution.quote_rules import LIVE, QuoteRules
from ..settings import SchoolSettings
from .account_laws import BrakeLaw, DailyStopLaw, ProtectedLaw
from .buckets import SchoolBuckets
from .c2_laws import C2Law, MaxLossLaw, cap_numbers
from .law_set import SafetyLaws
from .margin_law import margin_room_law
from .quote_laws import GATE_REASONS, ImpossiblePriceLaw, QuoteGateLaw


def build_margin(cfg: dict) -> StressedMargin:
    """MS-P1m's margin per trade, one for the whole run (Drive is reached on first use)."""
    return build_road_margin(cfg)


def build_safety_laws(cfg: dict, settings: SchoolSettings, slot: Mapping[RoadCode, SlotSnapshot],
                      margin: StressedMargin) -> SafetyLaws:  # fmt: skip
    """The data checks before the limits, so a refusal's first reason is its root cause: a risk law that fails only
    because a quote is missing is a consequence of it (orchestrator, 22 Oct 2026). Every quote check under `LIVE`."""
    return laws_with(cfg, settings, slot, margin, LIVE)


def laws_with(cfg: dict, settings: SchoolSettings, slot: Mapping[RoadCode, SlotSnapshot], margin: StressedMargin,
              rules: QuoteRules) -> SafetyLaws:  # fmt: skip
    """The laws with the quote checks under `rules`; only `build_safety_laws` (live) and `practice_wiring` (the
    simulator) call it, and a test pins that no other module does."""
    books = profile_settings(cfg, RISK_PROFILE_BOOKS)
    costs = SimulatorTradeCosts(cfg["charges"])
    risks = PositionRisks(SchoolBuckets(books.bucket_sides), HeldMaxLoss(cfg["charges"]), costs)
    return SafetyLaws((
        ProtectedLaw(),
        *(QuoteGateLaw(reason, rules) for reason in GATE_REASONS),
        ImpossiblePriceLaw(),
        MaxLossLaw(settings.max_loss_rs, cfg["charges"], MaxLossPerTrade(costs, settings.max_loss_rs)),
        C2Law("bucket_cap", BucketCap(risks, settings.bucket_rs), RefusalReason.BUCKET_CAP, cap_numbers, slot),
        C2Law("open_risk", OpenRiskCap(risks, settings.open_risk_rs), RefusalReason.OPEN_RISK, cap_numbers, slot),
        C2Law("new_risk_day", NewRiskPerDay(risks, settings.new_risk_day_rs), RefusalReason.NEW_RISK_DAY, cap_numbers,
              slot),
        margin_room_law(margin, costs, slot),
        DailyStopLaw(settings.daily_stop_rs),
        BrakeLaw(settings.brake_rs),
    ))  # fmt: skip
