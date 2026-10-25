"""The page's data from live sources (stories FL1-1c and FL1-1d): the sealed issues (FL1's `RangeSource`), every
scored forecast with its band (`HistorySource`), the reasons' facts (`FactsSource`), the regular sessions, NSE's
official closes (`Outcomes`) and the evening's own close (`TodayCloses`). It decides every number the page shows, so
the renderers only draw. The method shown is the one with the lowest mean error on next-session forecasts over its
whole record (back-fill and live).

The morning edition shows the forecasts sealed the session before for today and the next sessions, against the last
official close. The evening edition checks today's forecast against the evening's own close (labelled provisional
until the official file confirms it the next morning), and shows today's new forecasts. A missing issue, a close not
read or stale scores is a system problem: the message says so in one line."""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import replace
from datetime import date, datetime

from ..constants import CALIBRATION_DAYS, EVENING, ISSUE_CLOSE, MORNING, UNDERLYINGS
from ..ranges import NoTodayCloses, Outcomes, RangeSource, SealedIssue, TodayCloses
from ..sessions import RegularSessions
from .cues import FAILED, Section, SectionView
from .drift import method_problems, stale
from .facts import FactsSource
from .history import HistorySource, ScorePoint, method_record
from .keypoints import evening_points, morning_points
from .model import (
    CLOSE_NOT_READ,
    NO_FORECAST_TODAY,
    DayShape,
    Horizon,
    IndexView,
    Outcome,
    PageView,
    Problem,
    RangeView,
    Timeline,
)
from .own_check import OwnCheck, band_of
from .plain import LIGHT_WORDS, day_short, light, when
from .reasons import reasons, recent_misses
from .today_view import day_shape, track_record, unchecked_why

LIVE = "Live, sealed"
SHOWN, HORIZONS = 30, ("N1", "N3")
DEFAULT_METHOD = "implied"  # with no scored history yet (owner, 21 Oct 2026: the best-proven method, implied)
NO_ISSUE = "{underlying}: today's forecast is missing (none written by {now:%H:%M})"
NO_FORECAST = "{underlying}: today's forecast is missing (none sealed on {issued:%a %d %b})"
READ_FAILED = "{name}: the read failed ({error})"
PRICE_AT = {"close": "close {day}", "read": "close today", "3pm": "3 pm price {day}"}


def _mean_error(points: list[ScorePoint]) -> float:
    return statistics.fmean(p.error_points for p in points) if points else float("inf")


class PageBuilder:
    def __init__(self, ranges: RangeSource, history: HistorySource, facts: FactsSource, sessions: RegularSessions,
                 underlyings: tuple[str, ...] = UNDERLYINGS, official: Outcomes | None = None,
                 today_closes: TodayCloses | None = None, sections: tuple[Section, ...] = (),
                 levels=None):  # fmt: skip
        self.ranges, self.history, self.facts, self.sessions = ranges, history, facts, sessions
        self.underlyings, self.official, self.today_closes = underlyings, official, today_closes or NoTodayCloses()
        self.sections, self.levels = sections, levels  # `levels`: the evening's table (`sections.levels.Levels`)
        self.checks = OwnCheck(ranges, sessions, self.today_closes, official)

    def build(self, day: date, now: datetime, edition: str = EVENING, alerts: tuple[str, ...] = (),
              checks: tuple[str, ...] = (), confirmation: tuple[str, ...] = ()) -> PageView:  # fmt: skip
        facts, drift, indices = self.facts.facts(day), [], []
        issued = day if edition == EVENING else self.sessions.previous(day)
        cues = self._cues(day, edition)
        system = [s.why for s in cues if s.status == FAILED]
        for underlying in self.underlyings:
            issue = self.ranges.sealed(underlying, issued, ISSUE_CLOSE)
            if issue is None:  # its seal (GitHub's push time) may show later; the seal checks judge it, not this page
                system.append(NO_ISSUE.format(underlying=underlying, now=now) if edition == EVENING
                              else NO_FORECAST.format(underlying=underlying, issued=issued))  # fmt: skip
            index, problems = self._index(underlying, day, edition, issue, facts, cues)
            if edition == EVENING and self.levels is not None:
                index, failed = self._levels(index, day)
                cues, system = cues + failed, system + [f.why for f in failed]
            indices.append(index)
            drift += [p for p in problems if p.method != "data"]
            system += [f"{p.group}: {p.text}" for p in problems if p.method == "data"]
        return PageView(day, LIVE, tuple(indices), tuple(drift), tuple(system), checks, alerts, edition,
                        confirmation, cues, self.sessions.next(day))  # fmt: skip

    def _levels(self, index: IndexView, day: date) -> tuple[IndexView, tuple[SectionView, ...]]:
        """The evening's levels table; a read error is a `failed` Section (said and alerted), never a crash."""
        try:
            return replace(index, levels=self.levels.levels(index.underlying, day)), ()
        except Exception as error:  # noqa: BLE001  a damaged file is that table's problem, never the page's
            name = f"{index.underlying} levels"
            return index, (SectionView(name, FAILED, why=READ_FAILED.format(name=name, error=type(error).__name__)),)

    def _cues(self, day: date, edition: str) -> tuple[SectionView, ...]:
        """Every Section in its one state; a read error is `failed` (said in the system line), never a crash."""
        views = []
        for section in self.sections:
            try:
                views.append(section.read(day, edition))
            except Exception as error:  # noqa: BLE001  any source error is that Section's, never the page's
                why = READ_FAILED.format(name=section.name, error=type(error).__name__)
                views.append(SectionView(section.name, FAILED, why=why))
        return tuple(views)

    def _points(self, underlying: str, day: date) -> dict[tuple[str, str], list[ScorePoint]]:
        by = defaultdict(list)
        for point in self.history.points(underlying):
            if point.target_day < day:
                by[(point.method, point.horizon)].append(point)
        return by

    def _price(self, underlying: str, day: date, edition: str, issue: SealedIssue | None,
               checked: Outcome | None) -> tuple[float, str]:  # fmt: skip
        """The level the page marks: the last official close in the morning, today's close as read in the evening;
        the issue's 3 pm price when neither is there."""
        if edition == MORNING and self.official is not None:
            previous = self.sessions.previous(day)
            close = self.official.close(underlying, previous)
            if close is not None:
                return close, PRICE_AT["close"].format(day=day_short(previous))
        if edition == EVENING and checked is not None:
            return checked.close, PRICE_AT["read"]
        return (issue.s_ref, PRICE_AT["3pm"].format(day=day_short(issue.day))) if issue else (0.0, "")

    def _expected_score(self, day: date, edition: str) -> date:
        """The newest session G13b has scored by this edition's time: its score step runs in the 14:33 routine, once
        NSE's official file (23:20 the night before) is archived, so at 08:50 the previous session is not scored yet."""
        return self.sessions.previous(day) if edition == EVENING else self.sessions.back(day, 2)

    def _index(self, underlying: str, day: date, edition: str, issue: SealedIssue | None, facts,
               cues: tuple[SectionView, ...]) -> tuple[IndexView, list[Problem]]:  # fmt: skip
        by = self._points(underlying, day)
        banded = sorted({m for (m, h), ps in by.items() if h == "N1" and any(p.band for p in ps)})
        best = min(banded, key=lambda m: _mean_error(by[(m, "N1")]), default=DEFAULT_METHOD)
        if edition == EVENING:
            checked, unread = self.checks.evening(underlying, day, best)
        else:
            scored = {p.target_day for p in by[(best, "N1")]}
            checked, unread = self.checks.morning(underlying, day, best, scored), None
        horizons, problems = [], [Problem(underlying, "data", unread)] if unread else []
        for horizon in HORIZONS:
            days = sorted({p.target_day for (m, h), ps in by.items() if h == horizon for p in ps})
            records = tuple(method_record(by[(m, horizon)], days, days[-SHOWN:], m == best)
                            for m in sorted({m for (m, h) in by if h == horizon}))  # fmt: skip
            problems += [p for r in records for p in method_problems(underlying, horizon, r, days[-20:])]
            row = issue.row(best, horizon) if issue else None
            points = tuple(Outcome(p.target_day, p.close, p.band, bool(p.inside_50), bool(p.inside_90), p.live)
                           for p in by[(best, horizon)] if p.band is not None)  # fmt: skip
            points += (checked,) if horizon == "N1" and checked else ()
            horizons.append(Horizon(Timeline(horizon, best, points, row.target_day if row else None,
                                             band_of(row) if row else None), records))  # fmt: skip
        n1, expected = horizons[0].timeline.points, self._expected_score(day, edition)
        issued = expected in self.history.targets(underlying, best, "N1") or self.checks.issued(
            underlying, expected, best
        )
        problems += stale(underlying, _last_scored(n1, day), expected, issued)
        today = tuple(RangeView(r.horizon, r.target_day, band_of(r), r.p_up,
                                when(self.sessions.ahead(day, r.target_day), r.target_day, day))
                      for r in (issue.rows if issue else ())
                      if r.forecaster == best and r.status == "ok" and r.target_day >= day)  # fmt: skip
        price, price_at = self._price(underlying, day, edition, issue, checked)
        last = n1[-SHOWN:]
        index = IndexView(underlying, price, price_at, best, today, False, sum(p.live for p in n1), CALIBRATION_DAYS,
                          tuple(horizons), sum(p.inside_90 for p in last), len(last),
                          recent_misses(n1, self.sessions.previous, facts))  # fmt: skip
        index = replace(index, track=track_record(n1))  # the light rates the live record (judge E on FL1-1f)
        state = light(index)
        wrong = tuple(p.day for p in reversed(last) if not p.inside_90)
        unchecked = _unchecked(edition, checked, unread)
        return replace(index, light=state, light_word=LIGHT_WORDS[state], wrong_days=wrong,
                       backtested=sum(not p.live for p in last), result=checked, unchecked=unchecked,
                       unchecked_why=self._unchecked_why(unchecked, day),
                       shape=self._shape(underlying, day) if edition == EVENING and checked else None,
                       why=self._why(day, edition, best, checked, facts, cues)), problems  # fmt: skip

    def _unchecked_why(self, unchecked: str, day: date) -> str:
        close_why = self.today_closes.why_missing(day) if unchecked == CLOSE_NOT_READ else ""
        return unchecked_why(unchecked, close_why, self.sessions.previous(day), day)

    def _shape(self, underlying: str, day: date) -> DayShape:
        previous = self.official.close(underlying, self.sessions.previous(day)) if self.official else None
        return day_shape(self.today_closes.levels(underlying, day), previous)

    def _why(self, day: date, edition: str, best: str, checked: Outcome | None, facts,
             cues: tuple[SectionView, ...]) -> tuple:  # fmt: skip
        if edition == MORNING:
            return morning_points(best, cues)
        missed = checked is not None and not checked.inside_90
        said = reasons(day, self.sessions.previous(day), facts, checked.close > checked.band.q95) if missed else ()
        return evening_points(checked, tuple(said), cues)


def _unchecked(edition: str, checked: Outcome | None, unread: str | None) -> str:
    """Why the evening has no result for today: the close was not read, or no forecast was issued for today."""
    if edition != EVENING or checked is not None:
        return ""
    return CLOSE_NOT_READ if unread else NO_FORECAST_TODAY


def _last_scored(points: tuple[Outcome, ...], day: date) -> date | None:
    """The newest officially scored session (today's own check is not a score)."""
    scored = [p.day for p in points if p.day < day]
    return scored[-1] if scored else None
