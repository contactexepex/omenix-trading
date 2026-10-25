"""Entry rules that read the road's own 15:00 spots (story 3.2): CS1 capped seller, DB1 debit buyer, DR1 directional
debit spread. Each needs its full window of earlier sessions and says "not enough history" until it has it."""

from ...constants import OPTION_CALL, OPTION_PUT
from ...research_data.calendar import CalendarError
from ...research_engine.structures import LongIronFly
from ..constants import NoTradeReason
from .card_params import CardParams
from .entry import DTE_MAX_KEY, DTE_MIN_KEY, WINDOW_LENGTH_KEY, EntryContext, Sizing
from .proposals import Plan
from .session_days import sessions_between
from .shapes import credit_vertical, debit_vertical


class _Windowed:
    """The card numbers all three share: the spot window, the expiry window and the sizing."""

    def __init__(self, params: CardParams):
        self.length = params.whole(WINDOW_LENGTH_KEY)
        self.dte_min, self.dte_max = params.whole(DTE_MIN_KEY), params.whole(DTE_MAX_KEY)
        self.sizing = Sizing.from_params(params)


class CappedSeller(_Windowed):
    """CS1: spot above (below) its window mean sells a bull put (bear call) spread, short one expected move out."""

    def plan(self, ctx: EntryContext) -> Plan | NoTradeReason:
        window = ctx.window(self.length)
        if window is None:
            return NoTradeReason.NOT_ENOUGH_HISTORY
        expiry = ctx.expiry_in(self.dte_min, self.dte_max)
        if expiry is None:
            return NoTradeReason.NO_EXPIRY_IN_WINDOW
        if ctx.spot == window.mean:
            return NoTradeReason.RULE_NOT_FIRED
        move = ctx.move(expiry)
        if move is None:
            return NoTradeReason.NO_VALID_QUOTES
        above = ctx.spot > window.mean
        shape = credit_vertical(OPTION_PUT, ctx.spot - move.straddle_mid) if above else credit_vertical(
            OPTION_CALL, ctx.spot + move.straddle_mid)  # fmt: skip
        return Plan(expiry, shape, ctx.wing_widths(self.sizing.max_wing_steps), self.sizing.expected_net_rs)


class DebitBuyer(_Windowed):
    """DB1: realised volatility of the window above the ATM straddle's implied move buys an iron fly."""

    def plan(self, ctx: EntryContext) -> Plan | NoTradeReason:
        window = ctx.window(self.length)
        if window is None:
            return NoTradeReason.NOT_ENOUGH_HISTORY
        expiry = ctx.expiry_in(self.dte_min, self.dte_max)
        if expiry is None:
            return NoTradeReason.NO_EXPIRY_IN_WINDOW
        move = ctx.move(expiry)
        if move is None:
            return NoTradeReason.NO_VALID_QUOTES
        try:
            sessions = sessions_between(ctx.calendar, ctx.session, expiry)
        except CalendarError:
            return NoTradeReason.NO_EXPIRY_IN_WINDOW  # the calendar cannot count the sessions to this expiry
        if window.straddle_equivalent(ctx.spot, sessions) <= move.straddle_mid:
            return NoTradeReason.RULE_NOT_FIRED
        return Plan(expiry, LongIronFly(), ctx.wing_widths(self.sizing.max_wing_steps), self.sizing.expected_net_rs)


class DirectionalDebit(_Windowed):
    """DR1: spot at its window high (low) buys a bull call (bear put) spread, the far leg `max_wing_steps` out."""

    def plan(self, ctx: EntryContext) -> Plan | NoTradeReason:
        window = ctx.window(self.length)
        if window is None:
            return NoTradeReason.NOT_ENOUGH_HISTORY
        expiry = ctx.expiry_in(self.dte_min, self.dte_max)
        if expiry is None:
            return NoTradeReason.NO_EXPIRY_IN_WINDOW
        at_high, at_low = ctx.spot >= window.high, ctx.spot <= window.low
        if at_high == at_low:  # neither, or a flat window where both hold: no direction
            return NoTradeReason.RULE_NOT_FIRED
        shape = debit_vertical(OPTION_CALL if at_high else OPTION_PUT)
        return Plan(expiry, shape, ctx.wing_widths(self.sizing.max_wing_steps), self.sizing.expected_net_rs)
