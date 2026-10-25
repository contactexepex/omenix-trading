"""The 15:45 report's forecast sections (story FL1-1). Two checks per underlying and target day, kept apart (judge 422):
- the seal check: each issue whose target is that day must be sealed (its receipt's GitHub push time) before the next
  regular session's 09:15 after its issue day, the story's rule and G13b's deadline, and G13b's own `late` verdict
  must not be set; a missing or late one is said and alerted. It needs no close, so it runs on the target's own day;
- the match: each forecast sealed in time against the day's official close, with G13b's own scores (never recomputed
  here). NSE archives the close in the evening (G13b, 21 Oct 2026: about 23:00-02:13 IST), so a day is matched in a
  later report, said in its header (owner, 21 Oct 2026: "15:45, match lags 1 day")."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from ..models import IST
from .constants import (
    HORIZON_SESSIONS,
    ISSUE_CLOSE,
    LATE,
    LEVELS,
    MATCH_HEADER,
    NO_ISSUE,
    NONE_EXPECTED,
    NOT_IN_TIME,
    NOT_SEALED_YET,
    SCORES_NOT_READY,
    SEAL_BY,
    SEALS_OK,
)
from .ranges import STATUS_OK, Outcomes, RangeRow, RangeScore, RangeSource, SealedIssue
from .sessions import RegularSessions


def opens(day: date) -> datetime:
    return datetime.combine(day, SEAL_BY, IST)


def sealed_in_time(issue: SealedIssue, deadline: datetime) -> bool:
    return not issue.late and issue.sealed_at is not None and issue.sealed_at < deadline


def band(row: RangeRow) -> str:
    return "/".join(f"{row.quantiles[level]:.0f}" for level in LEVELS)


def _hit(flag: bool | None) -> str:
    return "n/a" if flag is None else ("in" if flag else "out")


def _direction(row: RangeRow, s_ref: float, outcome: float) -> str:
    called, moved = row.quantiles[0.50] - s_ref, outcome - s_ref
    return "right" if called * moved > 0 else "wrong" if called * moved < 0 else "flat"


def score_line(row: RangeRow, score: RangeScore, s_ref: float) -> str:
    return (
        f"  {row.forecaster}: 5/25/50/75/95 {band(row)}; close {score.outcome:.2f}: 25-75 {_hit(score.inside_25_75)}, "
        f"5-95 {_hit(score.inside_05_95)}, median direction {_direction(row, s_ref, score.outcome)}, "
        f"quantile score {score.quantile_score:.2f}"
    )


@dataclass(frozen=True)
class Forecast:
    """One issue aimed at a target day: `issue` is None when it was never written."""

    horizon: str
    issue_day: date
    issue: SealedIssue | None
    in_time: bool


class MatchSection:
    def __init__(self, forecasts: RangeSource, outcomes: Outcomes, sessions: RegularSessions, issues_from: date | None):
        """`issues_from`: G13b's first live day (`daily.live_from.price_ranges`); no forecast is expected from an issue
        day before it (None: G13b is not live, none is expected), so going live raises no false "missing" alert."""
        self.forecasts, self.outcomes, self.sessions, self.issues_from = forecasts, outcomes, sessions, issues_from

    def aimed_at(self, underlying: str, target: date) -> list[Forecast]:
        """The forecasts expected for `target`, each with its issue (None when never written)."""
        found = []
        for horizon, sessions in HORIZON_SESSIONS.items():
            issue_day = self.sessions.back(target, sessions)
            if self.issues_from is None or issue_day < self.issues_from:
                continue
            issue = self.forecasts.sealed(underlying, issue_day, ISSUE_CLOSE)
            deadline = opens(self.sessions.next(issue_day))
            found.append(Forecast(horizon, issue_day, issue, issue is not None and sealed_in_time(issue, deadline)))
        return found

    def seal_lines(self, underlying: str, target: date) -> tuple[list[str], list[str]]:
        """(report lines, alert texts): every missing or late forecast for `target`."""
        alerts = []
        for forecast in self.aimed_at(underlying, target):
            what = {"underlying": underlying, "horizon": forecast.horizon, "issue_day": forecast.issue_day}
            if forecast.issue is None:
                alerts.append(NO_ISSUE.format(**what, target=target))
            elif not forecast.in_time:
                sealed = forecast.issue.sealed_at or "no push evidence"
                alerts.append(LATE.format(**what, target=target, sealed=sealed))
        expected = SEALS_OK if self.aimed_at(underlying, target) else NONE_EXPECTED
        return alerts or [expected.format(underlying=underlying, target=target)], alerts

    def match_lines(self, underlying: str, target: date) -> tuple[list[str], bool] | None:
        """(the match of `target`'s forecasts against its official close, whether it is complete), or None while the
        close is not archived. Complete means every ok row of every forecast sealed in time has G13b's score (judge
        422.1): until then the day is said to wait for its scores and a later report takes it up again."""
        if self.outcomes.close(underlying, target) is None:
            return None
        out = [MATCH_HEADER.format(underlying=underlying, target=target)]
        scores = self.forecasts.scores(underlying, target)
        for forecast in self.aimed_at(underlying, target):
            if not forecast.in_time:
                out.append(NOT_IN_TIME.format(horizon=forecast.horizon, issue_day=forecast.issue_day))
                continue
            lines = _scored(forecast, scores)
            if lines is None:
                return [SCORES_NOT_READY.format(underlying=underlying, target=target)], False
            out += [f" {forecast.horizon}, issued {forecast.issue_day} 15:45 at {forecast.issue.s_ref:.2f}:", *lines]
        return out, True


def _scored(forecast: Forecast, scores: list[RangeScore]) -> list[str] | None:
    """One line per ok row with its G13b score, or None while any ok row has no score yet."""
    found = {(s.forecaster, s.horizon, s.issue_day): s for s in scores}
    rows = sorted((r for r in forecast.issue.rows if r.horizon == forecast.horizon and r.status == STATUS_OK),
                  key=lambda r: r.forecaster)  # fmt: skip
    matched = [(row, found.get((row.forecaster, row.horizon, forecast.issue_day))) for row in rows]
    if any(score is None for _, score in matched):
        return None
    return [score_line(row, score, forecast.issue.s_ref) for row, score in matched]


def next_ranges(underlying: str, issue: SealedIssue | None, now: datetime) -> list[str]:
    """Today's 15:45 issue, shown only once sealed (pushed) by the time the report is built."""
    if issue is None or issue.late or issue.sealed_at is None or issue.sealed_at > now:
        return [NOT_SEALED_YET.format(underlying=underlying)]
    lines = [f"{underlying}: sealed ranges for the next sessions (from {issue.s_ref:.2f})"]
    for row in sorted(issue.rows, key=lambda r: (r.horizon, r.forecaster)):
        if row.status == STATUS_OK:
            up = "" if row.p_up is None else f", P(up) {row.p_up:.2f}"
            lines.append(f"  {row.horizon} ({row.target_day}) {row.forecaster}: 5/25/50/75/95 {band(row)}{up}")
    return lines
