"""The splice (story G14, design "The input history"): what a forecast for day `d` may read of the intraday RV, point
in time at `d`'s cutoff. For each session before `d`: the candle row when it is ok and first seen before the cutoff,
else the live A16 row when it is ok and first seen before the cutoff, else the session is missing. A void live row
does not block a later candle row (a candle row measures the same session; it is not a fill)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime

from ..forecast_v4_rules.candle_history import CandleSession
from ..forecast_v4_rules.series import SessionRv

CANDLE, LIVE = "candle", "live"


@dataclass(frozen=True)
class SplicedRv:
    rv: SessionRv  # the row read, as v4's forecasters take it
    source: str  # CANDLE or LIVE


def from_candle(sessions: list[CandleSession]) -> list[SessionRv]:
    """W8's reader's sessions (`candle_history`) as v4's forecasters take a row: void stays None."""
    return [SessionRv(s.day, s.rv_session, s.first_seen_at) for s in sessions]


def _usable(rows: list[SessionRv], d: date, cutoff: datetime) -> dict[date, SessionRv]:
    """The ok rows of sessions before `d` first seen before the cutoff, by session."""
    return {r.day: r for r in rows if r.day < d and r.value is not None and r.first_seen_at < cutoff}


def splice(candle: list[SessionRv], live: list[SessionRv], d: date, cutoff: datetime) -> list[SplicedRv]:
    """The candle-first series for `d`, in session order; a session with neither usable row is left out."""
    chosen = {day: SplicedRv(row, LIVE) for day, row in _usable(live, d, cutoff).items()}
    chosen |= {day: SplicedRv(row, CANDLE) for day, row in _usable(candle, d, cutoff).items()}
    return [chosen[day] for day in sorted(chosen)]


def source_counts(rows: list[SplicedRv]) -> str:
    """`candle:<n>;live:<m>`: how many inputs each source gave (both always named, so a mix is never hidden)."""
    counts = Counter(r.source for r in rows)
    return f"{CANDLE}:{counts[CANDLE]};{LIVE}:{counts[LIVE]}"
