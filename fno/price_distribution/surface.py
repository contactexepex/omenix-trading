"""An expiry's compact IV surface (G13 section 2): each out-of-the-money quote's IV and delta, the ATM IV, IV at the
10P, 25P, 25C and 10C delta points, and the 25-delta risk reversal and butterfly. IVs are fractions here; the record
converts them to points."""

from __future__ import annotations

from dataclasses import dataclass

from ..constants import OPTION_CALL, OPTION_PUT
from .chain import UsedQuotes
from .constants import DELTA_POINTS
from .pricing import delta, implied_vol


@dataclass(frozen=True)
class SmilePoint:
    strike: float
    kind: str
    iv: float
    delta: float


@dataclass(frozen=True)
class Surface:
    atm_strike: float | None
    atm_iv: float | None
    otm: tuple[SmilePoint, ...]  # by strike
    delta_ivs: dict[str, float | None]  # 10P, 25P, 25C, 10C
    risk_reversal_25: float | None
    butterfly_25: float | None


def is_otm(strike: float, kind: str, forward: float) -> bool:
    return strike < forward if kind == OPTION_PUT else strike >= forward


def otm_points(used: UsedQuotes, forward: float, days: int, rate: float) -> tuple[SmilePoint, ...]:
    points = []
    for q in sorted(used.quotes, key=lambda q: q.strike):
        if not is_otm(q.strike, q.kind, forward):
            continue
        iv = implied_vol(q.price, forward, q.strike, q.kind, days, rate)
        if iv is not None:
            points.append(SmilePoint(q.strike, q.kind, iv, delta(forward, q.strike, q.kind, days, rate, iv)))
    return tuple(points)


def atm(used: UsedQuotes, forward: float, days: int, rate: float) -> tuple[float | None, float | None]:
    """The strike nearest the forward (lower on a tie) with both sides used; the mean of its call and put IVs."""
    strikes = [k for k, _, _ in used.pairs()]
    if not strikes:
        return None, None
    strike = min(strikes, key=lambda k: (abs(k - forward), k))
    ivs = [implied_vol(used.mid(strike, kind), forward, strike, kind, days, rate) for kind in (OPTION_CALL, OPTION_PUT)]
    return strike, None if None in ivs else sum(ivs) / 2


def iv_at_delta(points: tuple[SmilePoint, ...], target: float) -> float | None:
    """Linear in delta between the two nearest quoted points around `target`; None outside the quoted deltas."""
    side = OPTION_PUT if target < 0 else OPTION_CALL
    ordered = sorted((p.delta, p.iv) for p in points if p.kind == side)
    for (d_lo, iv_lo), (d_hi, iv_hi) in zip(ordered, ordered[1:], strict=False):
        if d_lo <= target <= d_hi:
            return iv_lo if d_hi == d_lo else iv_lo + (target - d_lo) * (iv_hi - iv_lo) / (d_hi - d_lo)
    return next((iv for d, iv in ordered if d == target), None)


def surface(used: UsedQuotes, forward: float, days: int, rate: float) -> Surface:
    points = otm_points(used, forward, days, rate)
    atm_strike, atm_iv = atm(used, forward, days, rate)
    deltas = {name: iv_at_delta(points, target) for name, target in DELTA_POINTS.items()}
    put25, call25 = deltas["25P"], deltas["25C"]
    both = put25 is not None and call25 is not None
    reversal = call25 - put25 if both else None
    fly = (call25 + put25) / 2 - atm_iv if both and atm_iv is not None else None
    return Surface(atm_strike, atm_iv, points, deltas, reversal, fly)
