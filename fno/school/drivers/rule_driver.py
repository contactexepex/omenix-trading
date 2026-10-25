"""The rule drivers (story MS-P1e): one `Driver` for every card whose entry is a family rule. The family says what
to build (or why not); `ProposalBuilder` sizes it under the cap; the card's exit rule reviews open positions. A new
rule driver is a card file plus, at most, one new family; no engine code changes."""

from ..constants import ExitReason, NoTradeReason
from ..contracts.decisions import Decision, DriverCard, OpenPosition, SpotPoint
from ..contracts.roads import RoadDay
from ..contracts.snapshot import SlotSnapshot
from .card_params import CardParams
from .entry import EntryContext, Family
from .exits import ExitPlan
from .proposals import ProposalBuilder
from .scope import check_scope, no_trade, own_positions, trade
from .session_days import TradingCalendar

MAX_OPEN_KEY = "max_open_per_road"  # open positions of this driver version on one road before it stops (0: no limit)


class RuleDriver:
    def __init__(self, card: DriverCard, family: Family, exits: ExitPlan, builder: ProposalBuilder,
                 calendar: TradingCalendar):  # fmt: skip
        self.card, self.family, self.exits, self.builder, self.calendar = card, family, exits, builder, calendar
        self.max_open = CardParams(card).whole(MAX_OPEN_KEY)

    def decide(self, road_day: RoadDay, snapshot: SlotSnapshot, history: tuple[SpotPoint, ...],
               positions: tuple[OpenPosition, ...]) -> Decision:  # fmt: skip
        check_scope(self.card, road_day, snapshot)
        if self.max_open and len(own_positions(self.card, road_day, positions)) >= self.max_open:
            return no_trade(self.card, road_day, NoTradeReason.POSITION_OPEN)
        plan = self.family.plan(EntryContext(road_day, snapshot, history, self.calendar))
        if isinstance(plan, NoTradeReason):
            return no_trade(self.card, road_day, plan)
        proposal = self.builder.build(plan, road_day, snapshot)
        if proposal is None:
            reason = NoTradeReason.NO_STRUCTURE_UNDER_CAP
            if self.builder.quotes_missing(plan, snapshot):
                reason = NoTradeReason.NO_VALID_QUOTES
            return no_trade(self.card, road_day, reason)
        return trade(self.card, road_day, proposal)

    def review_exit(self, position: OpenPosition, snapshot: SlotSnapshot,
                    history: tuple[SpotPoint, ...]) -> ExitReason | None:  # fmt: skip
        return self.exits.review(position, snapshot, history, self.calendar)


class ReferenceDriver(RuleDriver):
    """REF: the matched control of each road. It differs from a rule driver only in its card and family (every
    session, a condor at one expected move, held to expiry)."""
