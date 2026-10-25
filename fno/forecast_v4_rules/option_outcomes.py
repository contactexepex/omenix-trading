"""V4's and V5's outcomes (PROTOCOL_v4.md sections 1.4 and 1.5; story G7b completion): the one place for these rules,
which G8 imports as it imports `series.py` for the others.

- V5: inside when NIFTY's final settlement of the frozen expiry is strictly within `K +/- P`, from NSE's F&O file of
  the expiry day only (`settlement.v5_outcome`, called). `first_seen_at`: Drive's `createdTime` of that raw file (A11's
  first archived version; raw files never change), else A8's release-check sighting, else unresolved, never "now".
- V4: realised volatility of the 5 sessions after `d` (A16's live intraday `RV_s`) below the pack's ATM implied
  volatility on the same session clock (`units.v4_outcome`, called). A void session voids the day; a missing one leaves
  it unresolved.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime

from ..constants import NIFTY_SYMBOL
from ..desk.settlement import SettlementError, SettlementPrices
from ..forecast_v4.settlement import V5Outcome, V5OutcomeError, v5_outcome
from ..forecast_v4.units import v4_outcome
from ..models import IST
from ..storage.creation_times import CreationTimes
from ..storage.raw_source import NseDailyFoSource
from .baselines import before
from .option_terms import OptionTerms
from .series import Outcome, SessionRv
from .v4_expiry import V4_MIN_SESSIONS


@dataclass(frozen=True)
class Refused:
    """A settlement offered for V5 that the protocol refuses (first seen before the expiry's close, wrong file)."""

    day: date
    reason: str


class V5Resolver:
    def __init__(self, settlements: SettlementPrices, created: CreationTimes,
                 sightings: Callable[[], dict[date, datetime]]):  # fmt: skip
        """`sightings()`: A8's first sighting per F&O file day (`release_times.first_seen_times`)."""
        self.settlements, self.created, self.sightings = settlements, created, sightings

    def resolve(self, terms: OptionTerms) -> V5Outcome | Refused | None:
        """None while unresolved (no file yet, or no first-seen time); refused when the file gives no one clear price
        or the protocol refuses the level (first seen before the expiry's close)."""
        try:
            final = self.settlements.final_settlement(NIFTY_SYMBOL, terms.expiry)
        except SettlementError as unclear:
            return Refused(terms.day, str(unclear))
        if final is None:
            return None
        first_seen = self.created.created_at(NseDailyFoSource.path_for(terms.expiry))
        first_seen = first_seen or self.sightings().get(terms.expiry)
        if first_seen is None:
            return None
        try:
            return v5_outcome(terms.strike, terms.premium, terms.expiry, final, first_seen)
        except V5OutcomeError as refused:
            return Refused(terms.day, str(refused))


def v5_base_outcome(day: date, outcome: V5Outcome) -> Outcome:
    """For V5's base rate: known on the IST date its file was first seen (strictly before a later day's cutoff)."""
    return Outcome(day, outcome.inside, outcome.first_seen_at.astimezone(IST).date())


@dataclass(frozen=True)
class V4Result:
    day: date
    below: bool | None  # None: void
    resolved_on: date  # the IST date the last of the 5 rows was first seen


def resolve_v4(terms: OptionTerms, rows: Sequence[SessionRv], sessions: Sequence[date]) -> V4Result | None:
    """`rows`: A16's live rows (`series.live_intraday_rv`, value None for a void session); `sessions`: the scored
    sessions in order. None while any of the 5 sessions after `d` has no row. A row with a negative or non-finite
    variance is a data fault that stops here (`units.v4_outcome` raises), never a void."""
    start = before(list(sessions), terms.day) + (terms.day in sessions)
    window = list(sessions[start : start + V4_MIN_SESSIONS])
    found = {r.day: r for r in rows}
    if len(window) < V4_MIN_SESSIONS or any(d not in found for d in window):
        return None
    picked = [found[d] for d in window]
    resolved_on = max(r.first_seen_at for r in picked).astimezone(IST).date()
    if any(r.value is None for r in picked):
        return V4Result(terms.day, None, resolved_on)
    below = v4_outcome([r.value for r in picked], terms.iv, terms.calendar_days, terms.sessions)
    return V4Result(terms.day, below, resolved_on)


def v4_base_outcome(result: V4Result) -> Outcome | None:
    """For V4's base rate: void days are never outcomes."""
    return None if result.below is None else Outcome(result.day, result.below, result.resolved_on)
