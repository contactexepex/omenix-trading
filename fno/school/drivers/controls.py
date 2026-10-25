"""The control drivers (story MS-P1e): N0 does nothing; RC1 draws a random trade under the same caps. Neither is ever
ranked, recommended or shown as a candidate (their cards say so)."""

import hashlib
import random
from collections.abc import Mapping
from datetime import date

from ...constants import OPTION_CALL, OPTION_PUT
from ...research_engine.structures import BOUGHT
from ...scoreboard.random_control import FLIPS, REDRAWS, WINDOW_STEPS
from ..constants import ExitReason, NoTradeReason
from ..contracts.decisions import Decision, DriverCard, OpenPosition, SpotPoint
from ..contracts.roads import RoadDay
from ..contracts.snapshot import SlotSnapshot
from .card_params import CardParams
from .entry import MAX_WING_STEPS_KEY, EntryContext
from .exits import ExitPlan
from .expected_move import ExpectedMove
from .families_condor import MIN_DTE_KEY
from .proposals import Plan, ProposalBuilder
from .scope import check_scope, no_trade, trade
from .session_days import TradingCalendar
from .shapes import BF, CCS, CDS, PCS, PDS, SC, TargetCondor, TargetFly, credit_vertical, debit_vertical

BASE_SHAPES = (PCS, CDS, BF, SC)  # one per family above; a flip gives the other direction (PCS<->CCS, CDS<->PDS)


class NothingDriver:
    """N0: never trades. Its decision each session is the sealed `no_trade: n0` that the pilot's denominator needs."""

    def __init__(self, card: DriverCard):
        self.card = card

    def decide(self, road_day: RoadDay, snapshot: SlotSnapshot, history: tuple[SpotPoint, ...],
               positions: tuple[OpenPosition, ...]) -> Decision:  # fmt: skip
        check_scope(self.card, road_day, snapshot)
        return no_trade(self.card, road_day, NoTradeReason.N0)

    def review_exit(self, position: OpenPosition, snapshot: SlotSnapshot,
                    history: tuple[SpotPoint, ...]) -> ExitReason | None:  # fmt: skip
        return None


def draw_seed(session: date, driver_id: str, road_code: str) -> int:
    digest = hashlib.sha256(f"{session.isoformat()}|{driver_id}|{road_code}".encode()).digest()
    return int.from_bytes(digest, "big")


class RandomDriver:
    """RC1: every session a random shape of the rule families, a random direction and a random strike within ten
    steps of the money, on a random recorded expiry with enough days left. The draw is seeded by SHA-256(session,
    driver, road), so replaying a day gives the same trade. A draw that cannot be built under the cap is redrawn
    (up to the research control's 20 times). The exit is the twin family's: `twin_exits` maps a shape's code (and
    `code@road` where a road differs) to the exit rule of the rule driver it copies."""

    def __init__(self, card: DriverCard, builder: ProposalBuilder, calendar: TradingCalendar,
                 twin_exits: Mapping[str, ExitPlan]):  # fmt: skip
        params = CardParams(card)
        self.card, self.builder, self.calendar, self.twin_exits = card, builder, calendar, dict(twin_exits)
        self.min_dte, self.max_wing_steps = params.whole(MIN_DTE_KEY), params.whole(MAX_WING_STEPS_KEY)

    def decide(self, road_day: RoadDay, snapshot: SlotSnapshot, history: tuple[SpotPoint, ...],
               positions: tuple[OpenPosition, ...]) -> Decision:  # fmt: skip
        check_scope(self.card, road_day, snapshot)
        ctx = EntryContext(road_day, snapshot, history, self.calendar)
        rng = random.Random(draw_seed(snapshot.session, self.card.driver_id, road_day.road.code))
        eligible = [e for e in snapshot.expiries if ctx.dte(e) >= self.min_dte]
        if not eligible:
            return no_trade(self.card, road_day, NoTradeReason.NO_EXPIRY_IN_WINDOW)
        expiry = rng.choice(eligible)
        move = ctx.move(expiry)
        if move is None:
            return no_trade(self.card, road_day, NoTradeReason.NO_VALID_QUOTES)
        for _ in range(REDRAWS):
            plan = Plan(expiry, self._draw_shape(rng, road_day.strike_step, ctx.spot, move),
                        ctx.wing_widths(self.max_wing_steps))  # fmt: skip
            proposal = self.builder.build(plan, road_day, snapshot)
            if proposal is not None:
                return trade(self.card, road_day, proposal)
        return no_trade(self.card, road_day, NoTradeReason.NO_STRUCTURE_UNDER_CAP)

    @staticmethod
    def _draw_shape(rng: random.Random, step: float, spot: float, move: ExpectedMove):
        code = rng.choice(BASE_SHAPES)
        if code in FLIPS and rng.random() < 0.5:
            code = FLIPS[code]
        anchor = move.atm_strike + rng.randint(-WINDOW_STEPS, WINDOW_STEPS) * step
        if code == SC:
            reach = abs(anchor - move.atm_strike) or step  # at least one step: both shorts on one strike is SF
            return TargetCondor(move.atm_strike + reach, move.atm_strike - reach)
        if code == BF:
            return TargetFly(BOUGHT, anchor)
        kind = OPTION_PUT if code in (PCS, PDS) else OPTION_CALL
        return credit_vertical(kind, anchor) if code in (PCS, CCS) else debit_vertical(kind, anchor)

    def review_exit(self, position: OpenPosition, snapshot: SlotSnapshot,
                    history: tuple[SpotPoint, ...]) -> ExitReason | None:  # fmt: skip
        rule = self.twin_exits.get(f"{position.structure}@{position.road}") or self.twin_exits.get(position.structure)
        if rule is None:
            raise KeyError(f"{self.card.driver_id}: no twin exit for {position.structure} on {position.road}")
        return rule.review(position, snapshot, history, self.calendar)
