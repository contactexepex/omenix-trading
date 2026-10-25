"""A plan turned into a sized proposal (story MS-P1e). D2's `CandidateBuilder` tries one width at a time, widest
first: it lists the legs on valid quotes, refuses prices outside the payoff bounds and keeps a width whose maximum
loss (C2's cost model: every charge and the Rs 1 pad) is within the cap at the mid. The school then prices the same
legs at the touch it will fill at (ask to buy, bid to sell) and keeps the width only if the cap still holds there,
so a wide spread cannot push a filled trade over the cap. One lot; nothing is invented."""

from dataclasses import dataclass, replace
from datetime import date

from ...constants import SIDE_BUY, SIDE_SELL, PlaybookStatus
from ...playbook.candidates import CandidateBuilder, NotBuilt, live_chain
from ...playbook.opportunities import SHADOW, Opportunity
from ...playbook.schema import Evidence, Strategy
from ...playbook.structure_spec import ExpiryRule, StructureSpec
from ...research_engine.features import DecisionContext
from ...research_engine.live_validation import LiveUseRule
from ...research_engine.structures import Leg, Structure, payoff_bounds, position_value, terminal_value
from ...risk.trade_costs import TradeCosts
from ..contracts.decisions import LegSpec, Proposal
from ..contracts.roads import RoadDay
from ..contracts.snapshot import SlotSnapshot
from .market_view import SnapshotMarket, snapshot_market

ONE_LOT = 1
TRADE_ID = "school"


@dataclass(frozen=True)
class Plan:
    """What a driver wants built: the shape on one expiry, the wing widths to try (points, widest first)."""

    expiry: date
    structure: Structure
    widths: tuple[float, ...]
    expected_net_rs: float = 0.0  # the card's frozen estimate behind the ranking score; 0 when it has none


class ProposalBuilder:
    def __init__(self, costs: TradeCosts, cap_rs: float):
        self.costs, self.cap = costs, cap_rs

    def build(self, plan: Plan, road_day: RoadDay, snapshot: SlotSnapshot) -> Proposal | None:
        view = snapshot_market(snapshot, plan.expiry)
        lot = road_day.lot_for(plan.expiry).units  # the plan's own expiry's lot (MS-P1a4), never the nearest's
        units = lot * ONE_LOT
        builder = CandidateBuilder({plan.structure.code: plan.structure}, self.costs, self.cap, lot)
        for width in plan.widths:
            try:
                candidate = builder.build(_opportunity(plan, width, snapshot), view.market, TRADE_ID)
            except NotBuilt:
                continue
            proposal = self._at_touch(candidate.proposal, view, plan, units)
            if proposal is not None:
                return proposal
        return None

    def quotes_missing(self, plan: Plan, snapshot: SlotSnapshot) -> bool:
        """True when no width of the plan has all its legs listed with valid quotes: the structure cannot be built
        for want of quotes, whatever the cap (D2's own listing test)."""
        market = snapshot_market(snapshot, plan.expiry).market
        chain = frozenset(live_chain(market, plan.expiry))
        return all(plan.structure.legs(chain, snapshot.spot, width) is None for width in plan.widths)

    def _at_touch(self, risk_proposal, view: SnapshotMarket, plan: Plan, units: int) -> Proposal | None:
        legs = [p.leg for p in risk_proposal.legs]
        prices = [_touch(view, p.contract, p.leg) for p in risk_proposal.legs]
        lowest, highest = payoff_bounds(legs)
        if not lowest < position_value(legs, prices) < highest:
            return None  # the touch itself is an impossible price for this position
        quotes = {p.contract: replace(view.market.quotes[p.contract], mid=price)
                  for p, price in zip(risk_proposal.legs, prices, strict=True)}  # fmt: skip
        max_loss = self.costs.max_loss(risk_proposal, replace(view.market, quotes=quotes))
        if max_loss > self.cap:
            return None
        specs = tuple(LegSpec(view.key_of(p.contract), _side(p.leg), ONE_LOT) for p in risk_proposal.legs)
        credit = -position_value(legs, prices)
        return Proposal(plan.structure.code, specs, risk_proposal.lot_size, credit * units, max_loss,
                        _costs(legs, credit, units, max_loss), plan.expected_net_rs / max_loss)  # fmt: skip


def _touch(view: SnapshotMarket, contract: str, leg: Leg) -> float:
    bid, ask = view.touch[contract]
    return ask if leg.bought else bid


def _side(leg: Leg) -> str:
    return SIDE_BUY if leg.bought else SIDE_SELL


def _costs(legs: list[Leg], credit_per_unit: float, units: int, max_loss: float) -> float:
    """What is not payoff loss in the maximum loss: entry and worst exit charges plus every pad."""
    payoff_loss = max(-(terminal_value(legs, leg.strike) + credit_per_unit) for leg in legs)
    return min(max(max_loss - payoff_loss * units, 0.0), max_loss)


def _opportunity(plan: Plan, width: float, snapshot: SlotSnapshot) -> Opportunity:
    """D2 wants a playbook version and cycle; the school fills in only what `CandidateBuilder` reads."""
    spec = StructureSpec(plan.structure.code, "", "", (width,), ONE_LOT, ExpiryRule("monthly", 1, 1, 0))
    strategy = Strategy(
        name=f"school-{plan.structure.code}", version=1, status=PlaybookStatus.RESEARCH, payer="", edge_family="school",
        structure=spec, entry_conditions=(), live_use_rule=LiveUseRule(), size_rule="1 lot", funding={}, exits={},
        evaluation_plan={"expected_net_per_opportunity": plan.expected_net_rs},
        evidence=Evidence(None, None, None, None, None, None), parameters_sha256="")  # fmt: skip
    return Opportunity(strategy, DecisionContext(plan.expiry, snapshot.session, plan.expiry), SHADOW)
