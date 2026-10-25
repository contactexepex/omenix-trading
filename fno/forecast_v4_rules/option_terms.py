"""The pack-frozen terms of V4 and V5 (PROTOCOL_v4.md sections 1.4 and 1.5; story G7b completion, parts c and d). Each
day either has terms or is void with its reason, counted, never filled. The inputs are the pack's fields, passed in
plainly so this module does not depend on the pack's file format (G10's), only on its quote shapes."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from ..constants import OPTION_CALL, OPTION_PUT
from ..forecast_v4.terms import CALENDAR_DAYS_A_YEAR
from ..forecast_v4.units import implied_vol_session_clock
from ..research_data.calendar import CalendarError, SessionCalendar
from ..research_data.expiries import monthly_expiries
from ..research_engine.implied_vol import ImpliedVolModel, OptionPricing
from ..v4_pack.model import ChainQuote
from .live_quotes import NO_QUOTE, TwoSided, quote_problem
from .v4_expiry import V4_MIN_SESSIONS, scored_sessions_until

IV_UNSOLVED, NO_FUTURE_QUOTE = "iv_unsolved", "no_future_quote"
FUTURE_NOT_MONTHLY, EXPIRY_LIST_UNAVAILABLE = "future_not_monthly", "expiry_list_unavailable"
NO_V4_EXPIRY, V4_EXPIRY_MISMATCH = "no_v4_expiry", "v4_expiry_mismatch"
ForwardOf = Callable[[float, float, float, float], float]  # (strike, call mid, put mid, years) -> F
PAST_CALENDAR = "calendar"  # the expiry lies past A7's calendar: the session count is unknown (as G4's label)


@dataclass(frozen=True)
class Void:
    day: date
    reason: str


@dataclass(frozen=True)
class OptionTerms:
    """One expiry's frozen terms: K, the forward, the two legs' Black-76 IVs and the clocks."""

    day: date
    expiry: date
    strike: float
    forward: float
    call_mid: float
    put_mid: float
    call_iv: float
    put_iv: float
    sessions: int  # S_e: scored sessions in (day, expiry]
    calendar_days: int  # C_e

    @property
    def premium(self) -> float:
        """V5's P: the K call's mid plus the K put's mid."""
        return self.call_mid + self.put_mid

    @property
    def iv(self) -> float:
        return (self.call_iv + self.put_iv) / 2

    @property
    def years(self) -> float:
        return self.calendar_days / CALENDAR_DAYS_A_YEAR

    @property
    def sigma_iv_session_clock(self) -> float:
        """V4's implied side on the session clock (protocol 1.4, `units.py`)."""
        return implied_vol_session_clock(self.iv, self.calendar_days, self.sessions)


def atm_strike(quotes: Sequence[ChainQuote], spot: float) -> float | None:
    """The strike nearest spot among those held; a tie goes to the lower strike (as G1)."""
    strikes = sorted({q.strike for q in quotes})
    return min(strikes, key=lambda k: (abs(k - spot), k)) if strikes else None


def leg(quotes: Sequence[ChainQuote], strike: float, kind: str) -> TwoSided | None:
    found = next((q for q in quotes if q.strike == strike and q.kind == kind), None)
    return None if found is None else TwoSided(found.bid, found.ask, found.last_trade_time)


class OptionTermsRule:
    def __init__(self, model: ImpliedVolModel, rate: float, calendar: SessionCalendar):
        self.model, self.rate, self.calendar = model, rate, calendar

    def v5(self, day: date, spot: float, chain: Sequence[ChainQuote], future_expiry: date, future: TwoSided | None,
           listed: Sequence[date] | None) -> OptionTerms | Void:  # fmt: skip
        """V5: `e` is the pack future's expiry, checked against NSE's listed monthlies known before `day` (`None`: no
        list could be read; an empty list has no monthly, so it voids as `future_not_monthly`); F is the future's mid
        under the live-quote rule. `monthly_expiries` takes each month's last listed expiry: a weekly pulled back into
        a month by a holiday would read as that month's monthly, and the day voids (safe, never a wrong expiry)."""
        if listed is None:
            return Void(day, EXPIRY_LIST_UNAVAILABLE)
        after = sorted(m for m in monthly_expiries(set(listed)) if m > day)
        if not after or future_expiry != after[0]:
            return Void(day, FUTURE_NOT_MONTHLY)
        if future is None or future.bid is None or future.ask is None:
            return Void(day, NO_FUTURE_QUOTE)
        if problem := quote_problem(future, day):
            return Void(day, problem)
        return self._terms(day, spot, chain, future_expiry, lambda strike, call, put, years: future.mid, NO_QUOTE)

    def v4(self, day: date, spot: float, chain: Sequence[ChainQuote], v4_expiry: date | None) -> OptionTerms | Void:
        """V4: `e` only from the pack's `v4_expiry`; F from put-call parity at K (weekly expiries have no future)."""
        if v4_expiry is None:
            return Void(day, NO_V4_EXPIRY)
        sessions = self._sessions(day, v4_expiry)
        if sessions is None:
            return Void(day, PAST_CALENDAR)
        if sessions < V4_MIN_SESSIONS:
            return Void(day, V4_EXPIRY_MISMATCH)
        return self._terms(day, spot, chain, v4_expiry, self._parity_forward, NO_V4_EXPIRY)

    def _parity_forward(self, strike: float, call_mid: float, put_mid: float, years: float) -> float:
        """`F = K + e^(r C_e / 365) (C_mid - P_mid)` (protocol 1.4)."""
        return strike + math.exp(self.rate * years) * (call_mid - put_mid)

    def _sessions(self, day: date, expiry: date) -> int | None:
        try:
            return scored_sessions_until(day, expiry, self.calendar)
        except CalendarError:
            return None

    def _terms(self, day: date, spot: float, chain: Sequence[ChainQuote], expiry: date, forward_of: ForwardOf,
               legs_missing: str) -> OptionTerms | Void:  # fmt: skip
        """`legs_missing`: the void reason when the expiry's ATM call or put is not in the pack."""
        quotes = [q for q in chain if q.expiry == expiry]
        strike = atm_strike(quotes, spot)
        call = None if strike is None else leg(quotes, strike, OPTION_CALL)
        put = None if strike is None else leg(quotes, strike, OPTION_PUT)
        if call is None or put is None:
            return Void(day, legs_missing)
        if problem := quote_problem(call, day) or quote_problem(put, day):
            return Void(day, problem)
        calendar_days = (expiry - day).days
        years = calendar_days / CALENDAR_DAYS_A_YEAR
        forward = forward_of(strike, call.mid, put.mid, years)
        ivs = [self._iv(q.mid, forward, strike, kind, years) for q, kind in ((call, OPTION_CALL), (put, OPTION_PUT))]
        if None in ivs:
            return Void(day, IV_UNSOLVED)
        sessions = self._sessions(day, expiry)
        if sessions is None:
            return Void(day, PAST_CALENDAR)
        return OptionTerms(day, expiry, strike, forward, call.mid, put.mid, ivs[0], ivs[1], sessions, calendar_days)

    def _iv(self, price: float, forward: float, strike: float, kind: str, years: float) -> float | None:
        return self.model.implied_vol(OptionPricing(price, forward, strike, kind, years, self.rate))
