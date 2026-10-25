"""Composition root of `fno/school/drivers/` (story MS-P1e): the only place that names the concrete families,
control drivers and the card-to-driver map. `build_drivers` takes its ports (costs, calendar); `build_school_drivers`
reads them from config.yaml and the card folder."""

from collections.abc import Callable, Mapping
from pathlib import Path

from ..contracts.decisions import Driver, DriverCard
from .card_params import CardError, CardParams
from .cards import CARDS_FOLDER, load_cards
from .controls import NothingDriver, RandomDriver
from .entry import Family
from .exits import ExitPlan
from .families_condor import Edge1Control, Reference, WeeklySeller, WidthLadder
from .families_directional import CappedSeller, DebitBuyer, DirectionalDebit
from .proposals import ProposalBuilder
from .rule_driver import ReferenceDriver, RuleDriver
from .session_days import TradingCalendar
from .shapes import BF, CCS, CDS, PCS, PDS, SC

FAMILIES: Mapping[str, Callable[[CardParams], Family]] = {
    "capped_seller": CappedSeller,
    "debit_buyer": DebitBuyer,
    "directional_debit": DirectionalDebit,
    "weekly_seller": WeeklySeller,
    "width_ladder": WidthLadder,
    "reference": Reference,
    "edge1_control": Edge1Control,
}
NOTHING, RANDOM, REFERENCE = "nothing", "random", "reference"

# RC1's twin: the shape it draws -> the rule driver whose exit it copies (story 3.2). The condor's twin is the ladder
# on the monthly roads and WS1 on the weekly road.
TWIN_CARDS = {PCS: "CS1", CCS: "CS1", BF: "DB1", CDS: "DR1", PDS: "DR1", SC: "PS4", f"{SC}@NIFTY-W": "WS1"}


def build_drivers(
    cards: Mapping[str, DriverCard], builder: ProposalBuilder, calendar: TradingCalendar
) -> tuple[Driver, ...]:
    drivers: list[Driver] = []
    for card in cards.values():
        if card.family == NOTHING:
            drivers.append(NothingDriver(card))
        elif card.family == RANDOM:
            drivers.append(RandomDriver(card, builder, calendar, _twin_exits(cards)))
        else:
            drivers.append(_rule_driver(card, builder, calendar))
    return tuple(drivers)


def _rule_driver(card: DriverCard, builder: ProposalBuilder, calendar: TradingCalendar) -> RuleDriver:
    if card.family not in FAMILIES:
        raise CardError(f"{card.driver_id}: unknown family {card.family!r}")
    params = CardParams(card)
    kind = ReferenceDriver if card.family == REFERENCE else RuleDriver
    return kind(card, FAMILIES[card.family](params), ExitPlan.from_params(params), builder, calendar)


def _twin_exits(cards: Mapping[str, DriverCard]) -> dict[str, ExitPlan]:
    missing = sorted({code for code in TWIN_CARDS.values() if code not in cards})
    if missing:
        raise CardError(f"RC1 copies the exits of {missing}, whose cards are missing")
    return {shape: ExitPlan.from_params(CardParams(cards[code])) for shape, code in TWIN_CARDS.items()}


def build_school_drivers(cfg: dict, root: Path) -> tuple[Driver, ...]:
    """Every card in `research/school/cards/`, priced with C2's cost model on the configured charges and capped at
    the school's per-trade limit, with the NSE session calendar for the session-count rules."""
    from ...composition import build_session_calendar
    from ...research_engine.cycles import TradingDays
    from ...risk.trade_costs import SimulatorTradeCosts
    from ..settings import school_settings

    builder = ProposalBuilder(SimulatorTradeCosts(cfg["charges"]), school_settings(cfg).max_loss_rs)
    return build_drivers(load_cards(root / CARDS_FOLDER), builder, TradingDays(build_session_calendar()))
