"""The stated rule and the two baselines (story section "The rule"), for one contract of G13's 3 pm record on day d:

1. the forward's quantiles one session ahead: `F_q = F exp(-s^2 h / 2 + z_q s sqrt(h))`, `s` the expiry's ATM IV and
   `h` the calendar days from d to d+ over 365 (G13's `years`);
2. the contract keeps its own IV of d (sticky strike); 3. one day less: Black-76 at `days - (d+ - d)` with G13's rate;
4. a call's quantiles are its values at `F_q` in order, a put's the same values reversed. No fitted parameter."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

from ..constants import OPTION_CALL
from ..price_distribution.pricing import black76_price, years
from .constants import LEVELS

Z = tuple(NormalDist().inv_cdf(level) for level in LEVELS)


@dataclass(frozen=True)
class ContractInputs:
    strike: float
    side: str  # CE or PE
    mid: float  # d's 3 pm mid
    iv: float  # the contract's own IV on d (fraction)
    forward: float
    atm_iv: float  # the expiry's ATM IV on d (fraction)
    days: int  # calendar days to expiry on d
    rate: float


def forward_quantiles(forward: float, atm_iv: float, step_days: int) -> tuple[float, ...]:
    h = years(step_days)
    return tuple(forward * math.exp(-atm_iv * atm_iv * h / 2 + z * atm_iv * math.sqrt(h)) for z in Z)


def rule_range(c: ContractInputs, step_days: int) -> tuple[float, ...]:
    """The five premium quantiles at d+ (rupees), monotone by construction."""
    left = c.days - step_days
    values = [black76_price(f, c.strike, c.side, left, c.rate, c.iv)
              for f in forward_quantiles(c.forward, c.atm_iv, step_days)]  # fmt: skip
    return tuple(values if c.side == OPTION_CALL else reversed(values))


def decay_only(c: ContractInputs, step_days: int) -> tuple[float, ...]:
    """The forward and IV unchanged, one day less: a point."""
    return (black76_price(c.forward, c.strike, c.side, c.days - step_days, c.rate, c.iv),) * len(LEVELS)


def no_change(c: ContractInputs) -> tuple[float, ...]:
    """A point at d's mid."""
    return (c.mid,) * len(LEVELS)
