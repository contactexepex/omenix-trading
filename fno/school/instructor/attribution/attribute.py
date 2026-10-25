"""The P&L attribution of one closed path (story MS-INS, part b; method frozen in the story). Per step between
consecutive complete points and per leg, with signed units and Black-76 Greeks at the step's start: delta x dF,
1/2 gamma x dF^2, vega x d(sigma), theta x dt. Costs are the fills' C1 charges plus the spread paid against the mids
of the path's own first and last snapshots, measured here from the fills (the outcome record's `slippage_vs_mid` is
not read). The residual balances, so the components less the costs are the net. A net that is not its fills' cash is
never attributed (judge 503): the residual would hide the gap."""

from dataclasses import dataclass

from ....constants import SIDE_BUY
from ....models import IST
from ..contracts import Attribution, HeldPath, net_matches_fills, record_sha256
from ..thresholds import POOR_FIT_RS, POOR_FIT_SHARE
from .greeks import greeks
from .points import Point, settlement_point, signed_units, snapshot_point


@dataclass
class Components:
    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    theta: float = 0.0
    iv_unsolved: int = 0

    @property
    def total(self) -> float:
        return self.delta + self.gamma + self.vega + self.theta

    @property
    def size(self) -> float:
        return abs(self.delta) + abs(self.gamma) + abs(self.vega) + abs(self.theta)


def attribute(path: HeldPath, rate: float, rules_sha256: str) -> Attribution | None:
    """None when the path cannot be attributed: a data fault, or no mid at entry or exit (fills rest on two-sided
    quotes, so that is a data fault too, and part c tags it so)."""
    if not path.attributable or not net_matches_fills(path.outcome):
        return None  # a fault (a net that is not its fills' cash among them): never forced into the residual
    if len({leg.key.expiry for leg in path.outcome.entry.legs}) != 1:
        return None  # legs on two expiries: law 1 refuses those, and no payoff model values them
    units = signed_units(path.outcome.entry.legs)
    keys = tuple(sorted(units))
    points = [snapshot_point(s, keys, rate) for s in path.snapshots]
    if path.settlement is not None:
        points.append(settlement_point(path.settlement, keys))
    if not (points[0].complete(keys) and points[-1].complete(keys)):
        return None
    kept = [points[0]] + [p for p in points[1:-1] if p.complete(keys)] + ([points[-1]] if len(points) > 1 else [])
    parts = Components()
    for start, end in zip(kept, kept[1:]):
        add_step(parts, start, end, units, rate)
    merged = len(points) - len(kept) + path.sessions_skipped  # quotes missing, or the road closed that session
    return _record(path, parts, points[0], points[-1], len(kept) - 1, merged, rules_sha256)


def add_step(parts: Components, start: Point, end: Point, units: dict, rate: float) -> None:
    for key, signed in units.items():
        sigma, forward, end_sigma = start.sigmas[key], start.forwards[key.expiry], end.sigmas[key]
        at_expiry = end.years[key.expiry] == 0  # no volatility is left to read: the vega of the last step is 0
        if (
            sigma is None
            or forward is None
            or end.forwards[key.expiry] is None
            or (end_sigma is None and not at_expiry)
        ):
            parts.iv_unsolved += 1  # the leg's step goes wholly to the residual
            continue
        g = greeks(forward, key.strike, key.kind.value, start.years[key.expiry], rate, sigma)
        moved = end.forwards[key.expiry] - forward
        parts.delta += signed * g.delta * moved
        parts.gamma += signed * 0.5 * g.gamma * moved * moved
        parts.vega += signed * g.vega * (0.0 if at_expiry else end_sigma - sigma)
        parts.theta += signed * g.theta * (start.years[key.expiry] - end.years[key.expiry])


def spread_paid(legs, point: Point) -> float:
    """Rupees paid against the point's mids: above the mid to buy, below it to sell."""
    return sum((leg.price - point.mids[leg.key]) * leg.units * (1 if leg.side == SIDE_BUY else -1) for leg in legs)


def _record(path, parts: Components, first: Point, last: Point, steps: int, merged: int, rules_sha256: str):
    outcome = path.outcome
    charges = sum(leg.charges for leg in outcome.entry.legs + outcome.exit.legs)
    spread = spread_paid(outcome.entry.legs, first) + spread_paid(outcome.exit.legs, last)
    residual = outcome.net + charges + spread - parts.total
    poor = is_poor_fit(residual, parts.size)
    closed_on = outcome.exit.filled_at.astimezone(IST).date()
    return Attribution(outcome.position_id, outcome.driver_id, outcome.road, closed_on, outcome.is_ticket,
                       parts.delta, parts.gamma, parts.vega, parts.theta, residual, charges, spread, outcome.net,
                       steps, merged, parts.iv_unsolved, poor, rules_sha256, record_sha256(outcome))  # fmt: skip


def is_poor_fit(residual: float, size: float) -> bool:
    """Above both Rs 200 and 25% of the Greek components' absolute sum: shown beside the causes, never hidden."""
    return abs(residual) > POOR_FIT_RS and abs(residual) > POOR_FIT_SHARE * size
