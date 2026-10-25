"""One day's valuation of a chain (G13 section 2): per expiry the forward, quote counts, the surface, the implied
distribution and the smile values; across expiries the 30-day ATM IV from the frozen G1 interpolation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..forecast.iv30 import AtmIv30, interpolate_30d
from .chain import ChainDay, ExpiryChain, QuoteFilter, UsedQuotes, used_quotes
from .constants import MISSING, NOT_ELIGIBLE, OK
from .density import DistributionResult, implied_distribution
from .forward import averaged_forward
from .smile import ContractValue, Smile, contract_values, fit_smile
from .surface import Surface, surface

EXPIRED = "expiry on or before the day"
NO_FORWARD = "no strike with both a call and a put used: no parity forward"
NO_QUOTES = "no quotes used"


@dataclass(frozen=True)
class ExpiryValuation:
    expiry: date
    days: int
    status: str  # ok, missing (an input failed) or not_eligible (by rule)
    reason: str | None
    quoted: int
    used: UsedQuotes | None = None
    forward: float | None = None
    future: float | None = None
    surface: Surface | None = None
    distribution: DistributionResult | None = None
    smile: Smile | None = None
    smile_reason: str | None = None
    contracts: tuple[ContractValue, ...] = ()

    @property
    def problems(self) -> list[str]:
        """Input failures worth an alert: a missing expiry or a missing distribution (never a by-rule skip)."""
        found = [self.reason] if self.status == MISSING else []
        if self.distribution is not None and self.distribution.distribution is None:
            found.append(f"distribution: {self.distribution.reason}")
        return [f"{self.expiry}: {p}" for p in found]


@dataclass(frozen=True)
class DayValuation:
    chain: ChainDay
    rate: float
    expiries: tuple[ExpiryValuation, ...]
    iv30: AtmIv30 | None

    def usable(self) -> list[ExpiryValuation]:
        """Expiries with a distribution, nearest first."""
        found = [e for e in self.expiries if e.distribution is not None and e.distribution.distribution is not None]
        return sorted(found, key=lambda e: e.expiry)

    @property
    def problems(self) -> list[str]:
        return [p for e in self.expiries for p in e.problems]


def value_expiry(chain: ExpiryChain, day: date, rule: QuoteFilter, rate: float) -> ExpiryValuation:
    days, quoted = (chain.expiry - day).days, len(chain.quotes)
    if days < 1:
        return ExpiryValuation(chain.expiry, days, NOT_ELIGIBLE, EXPIRED, quoted)
    used = used_quotes(chain, rule)
    if not used.quotes:
        return ExpiryValuation(chain.expiry, days, MISSING, NO_QUOTES, quoted, used, future=chain.future)
    forward = averaged_forward(used.pairs(), rate, days)
    if forward is None:
        return ExpiryValuation(chain.expiry, days, MISSING, NO_FORWARD, quoted, used, future=chain.future)
    found = surface(used, forward, days, rate)
    smile, smile_reason = fit_smile(found.otm, forward)
    return ExpiryValuation(chain.expiry, days, OK, None, quoted, used, forward, chain.future, found,
                           implied_distribution(used, forward, rate, days), smile, smile_reason,
                           contract_values(used, smile, forward, days, rate))  # fmt: skip


def value_day(chain: ChainDay, rule: QuoteFilter, rate: float) -> DayValuation:
    expiries = tuple(value_expiry(e, chain.day, rule, rate) for e in sorted(chain.expiries, key=lambda e: e.expiry))
    atm_points = {e.expiry: e.surface.atm_iv * 100 for e in expiries if e.surface and e.surface.atm_iv is not None}
    return DayValuation(chain, rate, expiries, interpolate_30d(chain.day, atm_points) if atm_points else None)
