"""The data series of protocol v4's questions (PROTOCOL_v4.md sections 1-2): regular-session NIFTY and India VIX
closes, the close-proxy session variance, the V6 big-move and V7 VIX-up outcomes with the session that resolves them,
and A16's live intraday session variance. The one place for these rules: G8 imports them to resolve outcomes (stories
G7 and G7b)."""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from datetime import date, datetime

from ..constants import SESSION_REGULAR
from ..forecast_v4.terms import BIG_MOVE, V1_INTRADAY_METHOD

A16_OK = "ok"  # fno/intraday/session_rv.py: a session's RV row is "ok" or "void"


@dataclass(frozen=True)
class DayValue:
    day: date
    value: float


@dataclass(frozen=True)
class Outcome:
    day: date  # the forecast day t
    value: bool
    resolved_on: date  # the session whose close settles it (known after that session's close)


@dataclass(frozen=True)
class SessionRv:
    """One A16 session row: `value` None when the session is void (never a value)."""

    day: date
    value: float | None
    first_seen_at: datetime


def closes_rows(text: str) -> list[dict]:
    """`warmup_closes.csv` (O6) rows of regular sessions only (muhurat and special sessions are never scored)."""
    rows = [r for r in csv.DictReader(io.StringIO(text)) if r["session"] == SESSION_REGULAR]
    return sorted(rows, key=lambda r: r["date"])


def regular_closes(rows: list[dict]) -> list[DayValue]:
    return [DayValue(date.fromisoformat(r["date"]), float(r["underlying"])) for r in rows]


def vix_closes(rows: list[dict]) -> list[DayValue]:
    """India VIX closes of the same regular sessions (for G8's V7); a row without a VIX close is left out."""
    return [DayValue(date.fromisoformat(r["date"]), float(r["vix"])) for r in rows if r.get("vix")]


def log_returns(closes: list[DayValue]) -> list[DayValue]:
    """Close-to-close log return of each regular session from the previous regular close (a special session's move
    sits inside the next regular return)."""
    return [DayValue(b.day, math.log(b.value / a.value)) for a, b in zip(closes, closes[1:], strict=False)]


def close_proxy_rv(closes: list[DayValue]) -> list[DayValue]:
    """`RV_s` = the squared close-to-close log return, kept exactly (a zero return is a zero RV)."""
    return [DayValue(r.day, r.value**2) for r in log_returns(closes)]


def big_move_outcomes(closes: list[DayValue], horizon: int) -> list[Outcome]:
    """V6a (horizon 1) and V6b (horizon 5): for forecast day t, whether any of the returns of t+1..t+horizon has an
    absolute value of at least 2%; resolved at t+horizon's close."""
    returns = log_returns(closes)
    out = []
    for i, start in enumerate(closes):
        window = returns[i : i + horizon]
        if len(window) == horizon:
            out.append(Outcome(start.day, any(abs(r.value) >= BIG_MOVE for r in window), window[-1].day))
    return out


def vix_up_outcomes(vix: list[DayValue], horizon: int, sessions: list[date]) -> list[Outcome]:
    """V7: for forecast day t, whether India VIX closes strictly higher at t+horizon than at t (a tie is "no"),
    resolved at t+horizon's close. `t+horizon` counts regular `sessions`, not VIX rows: a day whose own or
    t+horizon's VIX close is missing has no outcome (void), so a gap never stretches the horizon (judge 267)."""
    known = {v.day: v.value for v in vix}
    return [
        Outcome(t, known[end] > known[t], end)
        for t, end in zip(sessions, sessions[horizon:], strict=False)
        if t in known and end in known
    ]


def live_intraday_rv(rows: list[dict]) -> list[SessionRv]:
    """A16's live `rv/` rows (provenance live by construction: A16b writes `rv-candle/`, never read here), of the
    pinned method only (`terms.V1_INTRADAY_METHOD`): a row of any other method is not read."""
    out = []
    for r in rows:
        if r.get("method") != V1_INTRADAY_METHOD:
            continue
        value = float(r["rv_session"]) if r["status"] == A16_OK else None
        out.append(SessionRv(date.fromisoformat(r["session"]), value, datetime.fromisoformat(r["first_seen_at"])))
    return sorted(out, key=lambda s: s.day)
