"""The 13 cause rules of response 325 section 6.1 (story MS-INS, part c), each on the gathered evidence: True when it
fires, False when it does not, None when its inputs are missing ("not testable", counted, never guessed). A winner
(net >= 0) is read in each cause's winner form; causes 6 and 9 have none."""

from ...constants import ExitReason
from ..contracts import Cause
from ..thresholds import (
    COMPONENT_SHARE,
    GAP_STOP_MULTIPLE,
    MARKET_WIDE_COUNT,
    NOISE_SDS,
    RANGE_Z,
    SHOCK_Z,
    WHIPSAW_MULTIPLE,
)
from .evidence import PLAN_EXITS, Evidence

Verdict = bool | None


def verdicts(ev: Evidence) -> dict[Cause, Verdict]:
    return {
        Cause.MOVE_BEYOND_RANGE: None if ev.z is None else abs(ev.z) > RANGE_Z,
        Cause.WRONG_DIRECTION: _direction(ev),
        Cause.VOLATILITY_ROSE: _volatility(ev, short=True),
        Cause.VOLATILITY_COLLAPSED: _volatility(ev, short=False),
        Cause.TIME_DECAY: _time_decay(ev),
        Cause.GAP_THROUGH_STOP: _gap_through_stop(ev),
        Cause.SCHEDULED_EVENT_SHOCK: _event_shock(ev),
        Cause.UNSCHEDULED_SHOCK: _market_shock(ev),
        Cause.COSTS_ATE_EDGE: not ev.won and ev.gross >= 0,
        Cause.BAD_PRICE_OR_DATA: ev.data_fault,
        Cause.EXIT_WHIPSAW: _whipsaw(ev),
        Cause.NORMAL_NOISE: _noise(ev),
        Cause.RULE_BROKEN: None if ev.replay_matches is None else not ev.replay_matches,
    }


def _share(ev: Evidence, component: float) -> bool:
    """The component made at least its share of the loss (a loser) or of the gain (a winner). A flat result (net 0)
    has no share to explain: no component cause fires on it."""
    if ev.won:
        return ev.net > 0 and component >= COMPONENT_SHARE * ev.net
    return component <= -COMPONENT_SHARE * abs(ev.net)


def _event_shock(ev: Evidence) -> Verdict:
    if not ev.event_in_window:
        return False
    return None if ev.z is None else abs(ev.z) > SHOCK_Z


def _direction(ev: Evidence) -> Verdict:
    if ev.stance is not None and not ev.stance.directional:
        return False
    if ev.stance is None or ev.attribution is None or (not ev.won and ev.z is None):
        return None
    if ev.won:
        return ev.stance.directional and ev.attribution.delta > 0
    return ev.stance.directional and ev.attribution.delta < 0 and abs(ev.z) <= RANGE_Z


def _volatility(ev: Evidence, short: bool) -> Verdict:
    if ev.stance is None or ev.attribution is None:
        return None
    side = ev.stance.short_volatility if short else ev.stance.long_volatility
    return side and _share(ev, ev.attribution.vega)


def _time_decay(ev: Evidence) -> Verdict:
    if ev.stance is None or ev.attribution is None:
        return None
    if ev.won:
        return not ev.stance.long_premium and _share(ev, ev.attribution.theta)
    if not (ev.stance.long_premium and _share(ev, ev.attribution.theta)):
        return False
    return ev.inside_breakevens


def _gap_through_stop(ev: Evidence) -> Verdict:
    if ev.won or ev.exit_reason != ExitReason.LOSS_LIMIT:
        return False
    return None if ev.stop_rs is None else abs(ev.net) > GAP_STOP_MULTIPLE * ev.stop_rs


def _market_shock(ev: Evidence) -> Verdict:
    if ev.event_in_window:
        return False
    if sum(abs(z) > SHOCK_Z for z in ev.market) >= MARKET_WIDE_COUNT:
        return True
    return None if len(ev.market) < MARKET_WIDE_COUNT else False


def _whipsaw(ev: Evidence) -> Verdict:
    if ev.exit_reason not in PLAN_EXITS or (ev.won and ev.exit_reason != ExitReason.PROFIT_TARGET):
        return False
    if ev.hold_net is None:
        return None
    return ev.hold_net - ev.net > WHIPSAW_MULTIPLE * abs(ev.net)


def _noise(ev: Evidence) -> Verdict:
    if ev.noise is None or ev.attribution is None:
        return None
    a = ev.attribution
    market = a.delta + a.gamma + a.vega + a.theta + a.residual  # the mid-to-mid P&L
    mean, sd = ev.noise
    return abs(market - mean) <= NOISE_SDS * sd
