"""Each contract's market-implied chance of expiring in the money (story section 1), from one G13 day record: a put
at strike K is in the money with chance F(K), a call with 1 - F(K), where F is G13's stored risk-neutral CDF of that
expiry. F is rebuilt into G13's own `Distribution`, so the arithmetic is G13's, never a copy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..constants import OPTION_PUT
from ..price_distribution.constants import OK
from ..price_distribution.density import Distribution, Tail
from .constants import BODY, MEASURE, SOURCE_OF_LABEL, TAIL

NO_DISTRIBUTION = "no distribution for this expiry"


@dataclass(frozen=True)
class ContractChance:
    underlying: str
    day: date
    expiry: date
    days: int  # calendar days to expiry, G13's convention
    strike: float
    side: str  # CE or PE
    itm_chance: float
    region: str  # body or tail
    source: str  # 3pm or backfill_eod
    measure: str = MEASURE


@dataclass(frozen=True)
class ExpiryChances:
    """One expiry of one record: its chances, or the reason it has none."""

    underlying: str
    day: date
    expiry: date
    days: int
    source: str
    distribution: Distribution | None
    reason: str | None
    contracts: tuple[tuple[float, str], ...]  # (strike, side) of every contract G13 valued

    def chances(self) -> list[ContractChance]:
        if self.distribution is None:
            return []
        return [ContractChance(self.underlying, self.day, self.expiry, self.days, strike, side,
                               itm_chance(self.distribution, strike, side), region(self.distribution, strike),
                               self.source) for strike, side in self.contracts]  # fmt: skip


def itm_chance(distribution: Distribution, strike: float, side: str) -> float:
    below = distribution.cdf(strike)
    return below if side == OPTION_PUT else 1.0 - below


def region(distribution: Distribution, strike: float) -> str:
    return BODY if distribution.lower.strike <= strike <= distribution.upper.strike else TAIL


def distribution_of(expiry: dict) -> Distribution | None:
    """G13's `Distribution` rebuilt from an expiry's stored CDF points and tail anchors, or None."""
    stored = expiry.get("distribution") or {}
    if stored.get("status") != OK or expiry.get("forward") is None:
        return None
    return Distribution(
        forward=expiry["forward"], days=expiry["days"], points=tuple((k, c) for k, c in stored["cdf"]),
        raw_decreases=stored["raw_decreases"], lower=_tail(stored["lower_tail"]), upper=_tail(stored["upper_tail"]),
    )  # fmt: skip


def _tail(stored: dict) -> Tail:
    return Tail(stored["strike"], stored["cdf"], stored["iv_points"] / 100)


def _reason(expiry: dict) -> str:
    stored = expiry.get("distribution") or {}
    return expiry.get("reason") or stored.get("reason") or NO_DISTRIBUTION


def expiry_chances(record: dict) -> list[ExpiryChances]:
    """Every expiry of a G13 day record, nearest first."""
    day, source = date.fromisoformat(record["day"]), SOURCE_OF_LABEL[record["label"]]
    found = []
    for expiry in (record.get("valuation") or {}).get("expiries", []):
        distribution = distribution_of(expiry)
        contracts = tuple((c["strike"], c["kind"]) for c in expiry.get("contracts", []))
        found.append(ExpiryChances(record["underlying"], day, date.fromisoformat(expiry["expiry"]), expiry["days"],
                                   source, distribution, None if distribution else _reason(expiry),
                                   contracts if distribution else ()))  # fmt: skip
    return sorted(found, key=lambda e: e.expiry)
