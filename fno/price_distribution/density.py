"""The option-implied price distribution of one expiry (G13 section 2): a Breeden-Litzenberger CDF between adjacent
used strikes, made non-decreasing by one equally weighted pool-adjacent-violators pass, and one fixed lognormal tail
rule beyond the quoted strikes that keeps the measured edge mass. No fitted parameter. Risk-neutral, not a forecast.

Pinned (judge 304 should-fix 1): a strike pair more than 200 points apart forms no midpoint (left out before the pass);
every midpoint weighs the same; a quantile inside the measured CDF is linear in strike on the first segment
`c_i < p <= c_j` with `c_j > c_i`."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

from ..analytics import norm_cdf
from ..constants import OPTION_CALL, OPTION_PUT
from .chain import UsedQuotes
from .constants import BODY, DISTRIBUTION_LEVELS, MAX_MEAN_GAP, MAX_STRIKE_GAP, MIN_CDF_POINTS, TAIL
from .pricing import d1_d2, discount, implied_vol, years
from .surface import is_otm

INVERSE = NormalDist().inv_cdf
TOO_FEW_POINTS = "too few CDF points: {n} (at least {minimum})"
NO_EDGE_IV = "no implied volatility at the {side} edge strike {strike:g}"
MEAN_OFF = "mean {mean:.2f} is {gap:.3%} from the forward {forward:.2f} (limit {limit:.1%})"


@dataclass(frozen=True)
class Tail:
    strike: float  # the edge midpoint K_L or K_H
    cdf: float  # the measured CDF there, c_L or c_H
    vol: float  # the edge option's own IV


@dataclass(frozen=True)
class Distribution:
    forward: float
    days: int
    points: tuple[tuple[float, float], ...]  # (midpoint strike, CDF after the pass)
    raw_decreases: int
    lower: Tail
    upper: Tail

    def cdf(self, strike: float) -> float:
        lo, hi = self.lower, self.upper
        if strike < lo.strike:
            return lo.cdf * _put_side(self, strike, lo.vol) / _put_side(self, lo.strike, lo.vol)
        if strike > hi.strike:
            return 1 - (1 - hi.cdf) * _call_side(self, strike, hi.vol) / _call_side(self, hi.strike, hi.vol)
        for (k1, c1), (k2, c2) in zip(self.points, self.points[1:], strict=False):
            if k1 <= strike <= k2:
                return c1 if k2 == k1 else c1 + (strike - k1) * (c2 - c1) / (k2 - k1)
        return self.points[-1][1]

    def quantile(self, level: float) -> tuple[float, str]:
        """The strike at which the CDF reaches `level`, and whether it came from the body or a tail."""
        lo, hi = self.lower, self.upper
        if level < lo.cdf:
            return _lognormal_strike(self, lo.vol, -INVERSE(level * _put_side(self, lo.strike, lo.vol) / lo.cdf)), TAIL
        if level > hi.cdf:
            above = (1 - level) * _call_side(self, hi.strike, hi.vol) / (1 - hi.cdf)
            return _lognormal_strike(self, hi.vol, INVERSE(above)), TAIL
        if level == lo.cdf:
            return lo.strike, BODY
        for (k1, c1), (k2, c2) in zip(self.points, self.points[1:], strict=False):
            if c1 < level <= c2:
                return k1 + (level - c1) * (k2 - k1) / (c2 - c1), BODY
        return hi.strike, BODY

    def mean(self) -> float:
        """Exact for this distribution: each linear body segment's mass at its centre, plus the lognormal partial
        expectations of both tails scaled as the tails are."""
        body = sum((c2 - c1) * (k1 + k2) / 2 for (k1, c1), (k2, c2) in zip(self.points, self.points[1:], strict=False))
        lo, hi = self.lower, self.upper
        d1_lo, d2_lo = d1_d2(self.forward, lo.strike, lo.vol, self.days)
        d1_hi, d2_hi = d1_d2(self.forward, hi.strike, hi.vol, self.days)
        below = lo.cdf * self.forward * norm_cdf(-d1_lo) / norm_cdf(-d2_lo)
        above = (1 - hi.cdf) * self.forward * norm_cdf(d1_hi) / norm_cdf(d2_hi)
        return body + below + above

    def quantiles(self, levels: Sequence[float] = DISTRIBUTION_LEVELS) -> dict[float, tuple[float, str]]:
        return {level: self.quantile(level) for level in levels}


@dataclass(frozen=True)
class DistributionResult:
    distribution: Distribution | None
    reason: str | None  # why there is none (counted, never filled)


def _put_side(d: Distribution, strike: float, vol: float) -> float:
    return norm_cdf(-d1_d2(d.forward, strike, vol, d.days)[1])


def _call_side(d: Distribution, strike: float, vol: float) -> float:
    return norm_cdf(d1_d2(d.forward, strike, vol, d.days)[1])


def _lognormal_strike(d: Distribution, vol: float, d2: float) -> float:
    spread = vol * math.sqrt(years(d.days))
    return d.forward * math.exp(-(d2 * spread + 0.5 * spread * spread))


def put_curve(used: UsedQuotes, forward: float, rate: float, days: int) -> dict[float, float]:
    """Out-of-the-money puts as they are, out-of-the-money calls as puts by parity `P = C - e^{-rT}(F - K)`."""
    factor = discount(rate, days)
    curve = {}
    for q in used.quotes:
        if is_otm(q.strike, q.kind, forward):
            curve[q.strike] = q.price if q.kind == OPTION_PUT else q.price - factor * (forward - q.strike)
    return dict(sorted(curve.items()))


def raw_cdf(curve: dict[float, float], rate: float, days: int) -> list[tuple[float, float, float, float]]:
    """`(midpoint, CDF, lower strike, upper strike)` for each adjacent pair at most 200 points apart."""
    grow = 1 / discount(rate, days)
    strikes = list(curve)
    return [((a + b) / 2, grow * (curve[b] - curve[a]) / (b - a), a, b)
            for a, b in zip(strikes, strikes[1:], strict=False) if b - a <= MAX_STRIKE_GAP]  # fmt: skip


def pool_adjacent_violators(values: Sequence[float]) -> list[float]:
    """The non-decreasing sequence closest in squared distance, every value weighing the same."""
    blocks: list[list[float]] = []  # [mean, count]
    for value in values:
        blocks.append([value, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            mean2, n2 = blocks.pop()
            mean1, n1 = blocks.pop()
            blocks.append([(mean1 * n1 + mean2 * n2) / (n1 + n2), n1 + n2])
    return [mean for mean, n in blocks for _ in range(int(n))]


def implied_distribution(used: UsedQuotes, forward: float, rate: float, days: int) -> DistributionResult:
    curve = put_curve(used, forward, rate, days)
    raw = raw_cdf(curve, rate, days)
    if len(raw) < MIN_CDF_POINTS:
        return DistributionResult(None, TOO_FEW_POINTS.format(n=len(raw), minimum=MIN_CDF_POINTS))
    values = [c for _, c, _, _ in raw]
    pooled = [min(1.0, max(0.0, c)) for c in pool_adjacent_violators(values)]
    decreases = sum(1 for a, b in zip(values, values[1:], strict=False) if b < a)
    points = tuple((m, c) for (m, _, _, _), c in zip(raw, pooled, strict=True))
    tails = []
    for side, strike, kind in (("lower", raw[0][2], OPTION_PUT), ("upper", raw[-1][3], OPTION_CALL)):
        kind = kind if is_otm(strike, kind, forward) else (OPTION_CALL if kind == OPTION_PUT else OPTION_PUT)
        price = used.mid(strike, kind)
        vol = implied_vol(price, forward, strike, kind, days, rate) if price is not None else None
        if vol is None:
            return DistributionResult(None, NO_EDGE_IV.format(side=side, strike=strike))
        tails.append(vol)
    lower, upper = Tail(points[0][0], points[0][1], tails[0]), Tail(points[-1][0], points[-1][1], tails[1])
    found = Distribution(forward, days, points, decreases, lower, upper)
    mean = found.mean()
    gap = abs(mean / forward - 1)
    if gap > MAX_MEAN_GAP:
        return DistributionResult(None, MEAN_OFF.format(mean=mean, gap=gap, forward=forward, limit=MAX_MEAN_GAP))
    return DistributionResult(found, None)
