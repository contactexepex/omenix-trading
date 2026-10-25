"""The market state of a held position at each recorded point (story MS-INS, part b): each leg's mid and implied
volatility, each expiry's forward and the time left, read from a verified snapshot or, for a settled position, from
the settlement price at the expiry's 15:30 close (mid = intrinsic value, no time and no volatility left).

The forward is G13's parity forward, which counts whole calendar days; the pricing time counts minutes to 15:30. At a
6.5% rate the day's part changes the forward by about 0.0003 points per 100 of call minus put: negligible."""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time

from ....constants import SIDE_BUY
from ....models import IST
from ....price_distribution.forward import averaged_forward
from ...constants import OptionKind
from ...contracts.snapshot import ContractKey, SlotSnapshot
from .greeks import implied_vol

EXPIRY_CLOSE = time(15, 30)
MINUTES_PER_YEAR = 365 * 24 * 60


@dataclass(frozen=True)
class Point:
    years: dict[date, float]  # time to each expiry's close
    forwards: dict[date, float | None]  # None: no call and put pair to read it from
    mids: dict[ContractKey, float | None]  # None: no two-sided quote
    sigmas: dict[ContractKey, float | None]  # None: no quote, no forward, or no solvable volatility

    def complete(self, keys: Iterable[ContractKey]) -> bool:
        return all(self.mids.get(k) is not None for k in keys)


def years_left(at: datetime, expiry: date) -> float:
    close = datetime.combine(expiry, EXPIRY_CLOSE, IST)
    return max((close - at).total_seconds() / 60, 0.0) / MINUTES_PER_YEAR


def snapshot_point(snapshot: SlotSnapshot, keys: tuple[ContractKey, ...], rate: float) -> Point:
    expiries = sorted({k.expiry for k in keys})
    years = {e: years_left(snapshot.finished_at, e) for e in expiries}
    forwards = {e: forward_of(snapshot, e, rate) for e in expiries}
    mids = {k: finite_mid(snapshot, k) for k in keys}
    sigmas = {k: _sigma(mids[k], forwards[k.expiry], k, years[k.expiry], rate) for k in keys}
    return Point(years, forwards, mids, sigmas)


def settlement_point(settlement: float, keys: tuple[ContractKey, ...]) -> Point:
    expiries = {k.expiry for k in keys}
    return Point({e: 0.0 for e in expiries}, {e: settlement for e in expiries},
                 {k: intrinsic(k, settlement) for k in keys}, {k: None for k in keys})  # fmt: skip


def forward_of(snapshot: SlotSnapshot, expiry: date, rate: float) -> float | None:
    """G13's parity forward of the expiry at the snapshot, or None without a call and put pair."""
    return _finite(averaged_forward(_pairs(snapshot, expiry), rate, (expiry - snapshot.session).days))


def signed_units(legs) -> dict[ContractKey, int]:
    """Each filled leg's units, bought positive and sold negative."""
    return {leg.key: leg.units * (1 if leg.side == SIDE_BUY else -1) for leg in legs}


def finite_mid(snapshot: SlotSnapshot, key: ContractKey) -> float | None:
    """A two-sided quote's mid, or None: a NaN or infinite price never enters a forward or a volatility."""
    quote = snapshot.quote(key)
    return _finite(quote.mid) if quote else None


def intrinsic(key: ContractKey, level: float) -> float:
    return max(level - key.strike, 0.0) if key.kind == OptionKind.CALL else max(key.strike - level, 0.0)


def _finite(value: float | None) -> float | None:
    return value if value is not None and math.isfinite(value) else None


def _sigma(mid, forward, key: ContractKey, years: float, rate: float) -> float | None:
    if mid is None or forward is None:
        return None
    return implied_vol(mid, forward, key.strike, key.kind.value, years, rate)


def _pairs(snapshot: SlotSnapshot, expiry: date) -> list[tuple[float, float, float]]:
    """(strike, call mid, put mid) for every strike of the expiry with both sides two-sided: G13's parity input."""
    mids = {
        (k.strike, k.kind): m
        for k in snapshot.quotes
        if k.expiry == expiry and (m := finite_mid(snapshot, k)) is not None
    }
    return [(s, c, mids[(s, OptionKind.PUT)]) for (s, kind), c in sorted(mids.items())
            if kind == OptionKind.CALL and (s, OptionKind.PUT) in mids]  # fmt: skip
