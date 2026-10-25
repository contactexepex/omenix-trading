"""V5's outcome (PROTOCOL_v4.md section 1.5): where NIFTY settled at the frozen expiry, against K +/- P.

The level is the index's final settlement price of **that** expiry, read by E7's `NseFinalSettlement` from NSE's daily
F&O file of the expiry day only (`SttlmPric`, every expiring row agreeing). Never a later day's close, never another
expiry's level, never a level first seen before the expiry's 15:30 close. The record keeps the source file, its SHA-256
and when it was first seen (A11's first archived version), so the outcome can be replayed byte for byte.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from ..constants import NIFTY_SYMBOL
from ..desk.settlement import SETTLEMENT_TIME, FinalSettlement
from ..models import IST
from ..storage.raw_source import NseDailyFoSource


class V5OutcomeError(ValueError):
    """The level offered is not the frozen expiry's final settlement from its frozen source."""


@dataclass(frozen=True)
class V5Outcome:
    expiry: date
    inside: bool  # |level - K| < P: a straddle buyer held to expiry lost before costs
    level: float
    source: str
    source_sha256: str
    first_seen_at: datetime


def v5_outcome(
    strike: float, premium: float, expiry: date, final: FinalSettlement, first_seen_at: datetime
) -> V5Outcome:
    """`strike`, `premium` and `expiry` are the values frozen at 15:00 on the forecast day."""
    if not (strike > 0 and premium > 0):
        raise V5OutcomeError(f"K and P must be > 0, not {strike!r} and {premium!r}")
    if final.underlying != NIFTY_SYMBOL or final.expiry != expiry:
        raise V5OutcomeError(f"need {NIFTY_SYMBOL}'s settlement of {expiry}, not {final.underlying} {final.expiry}")
    if final.source != NseDailyFoSource.path_for(expiry):
        raise V5OutcomeError(f"the level must come from the expiry day's F&O file, not {final.source}")
    if first_seen_at.tzinfo is None or first_seen_at < datetime.combine(expiry, SETTLEMENT_TIME, IST):
        raise V5OutcomeError(f"first seen at {first_seen_at}: a settlement cannot exist before the expiry's close")
    inside = abs(final.price - strike) < premium
    return V5Outcome(expiry, inside, final.price, final.source, final.sha256, first_seen_at)
