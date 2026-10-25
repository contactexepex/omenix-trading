"""W8's one reader of A16b's candle-close history (owner, 24 Oct 2026: "W8 - yes"; story G7b completion): each
session's row of A16b's `rv-candle/` table, of A16b's pinned method and `backfilled` provenance only (any other row is
not read), void kept void. Yardstick A's ratio window (`pack_wiring.intraday_rv`), G8's W8 drift line and story G14
read it here and nowhere else; never a forecast input, outcome or base rate (decision 56 as the owner read it).
`paired_rv` is the one pairing of live and back-filled sessions: W8's drift line, its review trigger and G14's gap
table use it."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime

from ..global_cues.table import BACKFILLED
from ..intraday.realised_vol import CandleCloseRv15m
from .series import A16_OK

W8_CANDLE_METHOD = CandleCloseRv15m.method  # "rv-candle-15m-v1"


@dataclass(frozen=True)
class CandleSession:
    day: date
    status: str  # A16's "ok" or "void"
    rv_session: float | None  # None when void (never a value)
    method: str
    provenance: str
    first_seen_at: datetime


def candle_sessions(rows: list[dict]) -> list[CandleSession]:
    """A16b's rows (`CandleRvTable.rows()`) of the pinned method and provenance, in session order."""
    return sorted(
        (
            CandleSession(
                date.fromisoformat(r["session"]),
                r["status"],
                float(r["rv_session"]) if r["status"] == A16_OK else None,
                r["method"],
                r["provenance"],
                datetime.fromisoformat(r["first_seen_at"]),
            )  # fmt: skip
            for r in rows
            if r.get("method") == W8_CANDLE_METHOD and r.get("provenance") == BACKFILLED
        ),
        key=lambda s: s.day,
    )


@dataclass(frozen=True)
class PairedRv:
    day: date
    live: float  # A16's live session RV_s
    candle: float  # A16b's back-filled session RV_s
    ratio: float  # candle / live


def paired_rv(live: Mapping[date, float | None], candle: Mapping[date, float | None]) -> list[PairedRv]:
    """The sessions where both rows exist and are non-void (a zero live value pairs nothing), in session order."""
    return [
        PairedRv(day, value, candle[day], candle[day] / value)
        for day, value in sorted(live.items())
        if value and candle.get(day) is not None
    ]


def drift_days(paired: list[PairedRv]) -> list[tuple[date, float, float]]:
    """The pairs as `forecast_v4.diagnostics.proxy_drift` reads them: (day, candle, live), its ratio candle / live."""
    return [(p.day, p.candle, p.live) for p in paired]
