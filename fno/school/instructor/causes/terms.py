"""The terms the cause rules read (story MS-INS, part c), from a path's own points: the entry ATM straddle volatility,
the move `z` against it, the position's stance from its entry Greeks, its breakevens at expiry, and its model outcome
band for "normal noise". Pure functions: no port, no record."""

import math
from dataclasses import dataclass
from datetime import date
from statistics import NormalDist, fmean, pstdev

from ...constants import OptionKind
from ...contracts.snapshot import ContractKey, SlotSnapshot
from ..attribution.greeks import greeks, implied_vol, price
from ..attribution.points import Point, finite_mid, intrinsic, years_left
from ..thresholds import DIRECTIONAL_SHARE, NOISE_QUANTILES


@dataclass(frozen=True)
class Stance:
    short_volatility: bool  # net vega below 0
    long_volatility: bool  # net vega above 0
    directional: bool
    long_premium: bool  # a debit at entry


def atm_volatility(snapshot: SlotSnapshot, expiry: date, forward: float | None, rate: float) -> float | None:
    """The mean of the call and put volatility at the strike nearest the forward: the ATM straddle's."""
    strikes = sorted({k.strike for k in snapshot.quotes if k.expiry == expiry})
    if forward is None or not strikes:
        return None
    strike = min(strikes, key=lambda k: (abs(k - forward), k))
    years = years_left(snapshot.finished_at, expiry)
    vols = []
    for kind in OptionKind:
        mid = finite_mid(snapshot, ContractKey(expiry, strike, kind))
        vol = None if mid is None else implied_vol(mid, forward, strike, kind.value, years, rate)
        vols += [vol] if vol is not None else []
    return fmean(vols) if vols else None


def move_z(entry_level: float, exit_level: float, sigma: float | None, years_held: float) -> float | None:
    if sigma is None or years_held <= 0 or entry_level <= 0 or exit_level <= 0:
        return None
    return math.log(exit_level / entry_level) / (sigma * math.sqrt(years_held))


def stance(point: Point, units: dict, rate: float, max_loss: float, entry_premium: float) -> Stance | None:
    """None when a leg has no volatility or forward at entry: no stance can be read."""
    vega = delta = 0.0
    for key, signed in units.items():
        sigma, forward = point.sigmas.get(key), point.forwards.get(key.expiry)
        if sigma is None or forward is None:
            return None
        g = greeks(forward, key.strike, key.kind.value, point.years[key.expiry], rate, sigma)
        vega, delta = vega + signed * g.vega, delta + signed * g.delta * forward
    directional = abs(delta) * 0.01 >= DIRECTIONAL_SHARE * max_loss
    return Stance(vega < 0, vega > 0, directional, entry_premium < 0)


def inside_breakevens(units: dict, level: float, debit: float) -> bool:
    """A long-premium position's payoff at expiry at `level` is below the debit it paid."""
    return sum(signed * intrinsic(key, level) for key, signed in units.items()) < debit


def noise_band(entry: Point, units: dict, sigma: float, years_held: float, years_left: dict, rate: float):
    """The mean and standard deviation of the position's mid-to-mid P&L if the forward moved lognormally at the entry
    ATM volatility over the time held, each leg revalued at its own entry volatility (sticky strike), on a frozen grid
    of quantiles. None when a leg has no entry volatility or the time held is zero."""
    if years_held <= 0 or any(entry.sigmas.get(k) is None for k in units):
        return None
    normal, spread = NormalDist(), sigma * math.sqrt(years_held)
    outcomes = []
    for i in range(NOISE_QUANTILES):
        z = normal.inv_cdf((i + 0.5) / NOISE_QUANTILES)
        pnl = 0.0
        for key, signed in units.items():
            forward = entry.forwards[key.expiry] * math.exp(spread * z - spread * spread / 2)
            left = years_left[key.expiry]
            value = intrinsic(key, forward) if left <= 0 else price(forward, key.strike, key.kind.value, left, rate,
                                                                    entry.sigmas[key])  # fmt: skip
            pnl += signed * (value - entry.mids[key])
        outcomes.append(pnl)
    return fmean(outcomes), pstdev(outcomes)
