"""Entry rules that sell an iron condor or fly (story 3.2): WS1 weekly seller, PS2-4 width ladder, REF reference rule
and the EDGE1 measurement controls PS5 and KL1. Shorts sit one expected move out, except the controls, which keep
EDGE1's frozen strikes."""

from ...research_data.calendar import CalendarError
from ...research_engine.structures import ShortCondor, ShortIronFly, Structure
from ..constants import NoTradeReason
from .card_params import CardError, CardParams
from .entry import DTE_MAX_KEY, DTE_MIN_KEY, EntryContext, Sizing
from .proposals import Plan
from .session_days import sessions_between
from .shapes import ExpectedMoveCondor

SESSIONS_MIN_KEY, SESSIONS_MAX_KEY, MIN_DTE_KEY = "sessions_before_min", "sessions_before_max", "min_dte"
FIRST_IN_WINDOW_KEY, WIDTHS_KEY, SHAPE_KEY, SHORT_OFFSET_KEY = "first_in_window", "widths", "shape", "short_offset"
FLY, CONDOR = "fly", "condor"


def _condor_plan(ctx: EntryContext, expiry, sizing: Sizing) -> Plan | NoTradeReason:
    move = ctx.move(expiry)
    if move is None:
        return NoTradeReason.NO_VALID_QUOTES
    shape = ExpectedMoveCondor(ctx.spot, move.straddle_mid)
    return Plan(expiry, shape, ctx.wing_widths(sizing.max_wing_steps), sizing.expected_net_rs)


class WeeklySeller:
    """WS1: the nearest weekly expiry is `sessions_before_min` to `sessions_before_max` sessions away."""

    def __init__(self, params: CardParams):
        self.low, self.high = params.whole(SESSIONS_MIN_KEY), params.whole(SESSIONS_MAX_KEY)
        self.sizing = Sizing.from_params(params)

    @staticmethod
    def _sessions(ctx: EntryContext, expiry) -> int:
        try:
            return sessions_between(ctx.calendar, ctx.session, expiry)
        except CalendarError:
            return -1  # the calendar cannot count them: outside the window

    def plan(self, ctx: EntryContext) -> Plan | NoTradeReason:
        expiry = next((e for e in ctx.snapshot.expiries if e > ctx.session), None)
        if expiry is None or not self.low <= self._sessions(ctx, expiry) <= self.high:
            return NoTradeReason.NO_EXPIRY_IN_WINDOW
        return _condor_plan(ctx, expiry, self.sizing)


class WidthLadder:
    """PS2-4: the nearest expiry `dte_min` to `dte_max` days away; the three versions differ in `max_wing_steps`."""

    def __init__(self, params: CardParams):
        self.low, self.high = params.whole(DTE_MIN_KEY), params.whole(DTE_MAX_KEY)
        self.sizing = Sizing.from_params(params)

    def plan(self, ctx: EntryContext) -> Plan | NoTradeReason:
        expiry = ctx.expiry_in(self.low, self.high)
        return NoTradeReason.NO_EXPIRY_IN_WINDOW if expiry is None else _condor_plan(ctx, expiry, self.sizing)


class Reference:
    """REF: every session, the nearest recorded expiry with at least `min_dte` days left and a usable straddle."""

    def __init__(self, params: CardParams):
        self.min_dte = params.whole(MIN_DTE_KEY)
        self.sizing = Sizing.from_params(params)

    def plan(self, ctx: EntryContext) -> Plan | NoTradeReason:
        eligible = [e for e in ctx.snapshot.expiries if ctx.dte(e) >= self.min_dte]
        if not eligible:
            return NoTradeReason.NO_EXPIRY_IN_WINDOW
        return next((p for e in eligible if not isinstance(p := _condor_plan(ctx, e, self.sizing), NoTradeReason)),
                    NoTradeReason.NO_VALID_QUOTES)  # fmt: skip


class Edge1Control:
    """PS5 and KL1, measurement only: EDGE1's frozen entry day (the first session an expiry is 30-45 days away),
    strikes and fixed width list. The iron fly sells ATM; the condor sells at spot x (1 +- `short_offset`)."""

    def __init__(self, params: CardParams):
        self.low, self.high = params.whole(DTE_MIN_KEY), params.whole(DTE_MAX_KEY)
        flag = params.whole(FIRST_IN_WINDOW_KEY)
        if flag not in (0, 1):
            raise CardError(f"`{FIRST_IN_WINDOW_KEY}` must be 0 or 1, not {flag}")
        self.first_in_window = flag == 1
        self.widths = tuple(float(w) for w in params.text(WIDTHS_KEY).split(","))
        if list(self.widths) != sorted(set(self.widths), reverse=True):
            raise CardError(f"`{WIDTHS_KEY}` must be widest first, without repeats")
        self.shape = params.text(SHAPE_KEY)
        if self.shape not in (FLY, CONDOR):
            raise CardError(f"`{SHAPE_KEY}` must be {FLY} or {CONDOR}, not {self.shape!r}")
        self.offset = params.number(SHORT_OFFSET_KEY) if self.shape == CONDOR else None

    def plan(self, ctx: EntryContext) -> Plan | NoTradeReason:
        expiry = ctx.expiry_in(self.low, self.high, self.first_in_window)
        if expiry is None:
            return NoTradeReason.NO_EXPIRY_IN_WINDOW
        shape: Structure = ShortIronFly() if self.shape == FLY else ShortCondor(self.offset)
        return Plan(expiry, shape, self.widths)
