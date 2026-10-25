"""The live 15:45 issue (part A9), run by O1's `price_ranges` step, which alone passes `--live`. G13's exit contract:
not live or a hand run -> `nothing written: ...`, exit 0; a closed day -> `not a trading day`; a recorded issue is
never rebuilt and its stored problems count again; an unreadable chain or a failed build writes no file (a rerun can
still issue); a chain never captured is a `missing` record; any problem -> one line each, last line `written with
problems: ...`, exit 1; nothing captured anywhere -> `nothing written: ...`, exit 0. The command never alerts."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import date, datetime

import requests

from ..constants import SESSION_REGULAR
from ..forecast_v4_rules.series import DayValue
from ..price_distribution.chain import ChainSource
from ..price_distribution.sources import ChainUnavailable
from ..price_distribution.store import DistributionStore
from ..research_data.calendar import CalendarError, SessionCalendar
from ..storage.raw_store import RawFileConflict
from .build import CAPTURE, RangeBuilder, missing_issue
from .constants import ISSUE_1545, LIVE
from .folders import live_path
from .records import encode

NOT_LIVE = "nothing written: not live on {day} (config.yaml daily.live_from.price_ranges: {live_from})"
HAND_RUN = "nothing written: only O1's daily step writes live rows (--live); past days go through `pricerange backfill`"
NOT_TODAY = "nothing written: {day} is not today ({today})"
NOT_TRADING = "not a trading day"
NO_CHAIN = "no canonical 3 pm chain"
NOTHING = "nothing written: {reasons}"
BUILD_FAILED = "build failed ({kind}): {error}"
ALREADY = "{underlying}: already issued"
ALREADY_WITH = "{underlying}: already issued with {n} problems"
ISSUED = "{underlying}: issued ({n} problems)"
PROBLEM = "problem: {problem}"
WITH_PROBLEMS = "written with problems: {problems}"
DONE = "issued"
BEFORE_FAILED = "close tables or seals not updated ({kind}): {error}"
CONTAINED = (
    ValueError,
    ArithmeticError,
    RuntimeError,
    OSError,
    CalendarError,
    RawFileConflict,
    requests.RequestException,
)


class RangeIssuer:
    def __init__(self, chains: ChainSource, builder: RangeBuilder, closes: Callable[[str], Sequence[DayValue]],
                 store: DistributionStore, calendar: SessionCalendar, underlyings: Sequence[str],
                 live_from: date | None, now: Callable[[], datetime],
                 before: Callable[[date], list[str]] = lambda day: []):  # fmt: skip
        """`before(day)`: run first (BANKNIFTY's close table update); its lines are printed."""
        self.chains, self.builder, self.closes, self.store, self.calendar = chains, builder, closes, store, calendar
        self.underlyings, self.live_from, self.now, self.before = tuple(underlyings), live_from, now, before

    def issue(self, day: date, live: bool = True) -> tuple[int, list[str]]:
        now = self.now()
        refusal = self._refusal(day, now, live)
        if refusal:
            return 0, [refusal]
        lines, problems, absent, retry, written = [], [], {}, {}, 0
        try:
            lines += self.before(day)
        except CONTAINED as error:  # a close-table or seal failure is a problem line, never NIFTY's lost issue
            problems.append(BEFORE_FAILED.format(kind=type(error).__name__, error=error))
        for underlying in self.underlyings:
            path = live_path(underlying, day, ISSUE_1545)
            existing = self.store.get(path)
            if existing is not None:
                self.store.put(path, existing)
                stored = json.loads(existing).get("problems") or []
                problems += [f"{underlying} {p}" for p in stored]
                lines.append((ALREADY_WITH if stored else ALREADY).format(underlying=underlying, n=len(stored)))
                written += 1
                continue
            try:
                chain = self.chains.chain(underlying, day)
            except ChainUnavailable as error:
                retry[underlying] = str(error)
                continue
            if chain is None:
                absent[underlying] = NO_CHAIN
                continue
            try:
                record = self.builder.build(underlying, day, ISSUE_1545, chain, self.closes(underlying), CAPTURE,
                                            LIVE, now.isoformat())  # fmt: skip
            except CONTAINED as error:  # a refused row, a NaN, a closes read that failed: this underlying only
                retry[underlying] = BUILD_FAILED.format(kind=type(error).__name__, error=error)
                continue
            self.store.put(path, encode(record))
            written += 1
            lines.append(ISSUED.format(underlying=underlying, n=len(record["problems"])))
            problems += [f"{underlying} {p}" for p in record["problems"]]
        if len(absent) == len(self.underlyings):  # an earlier failure still fails the step (judge 416)
            nothing = NOTHING.format(reasons="; ".join(f"{u}: {r}" for u, r in absent.items()))
            return (1 if problems else 0), [*lines, *(PROBLEM.format(problem=p) for p in problems), nothing]
        for underlying, reason in absent.items():
            record = missing_issue(underlying, day, ISSUE_1545, LIVE, reason, self.builder.method, now.isoformat())
            self.store.put(live_path(underlying, day, ISSUE_1545), encode(record))
        problems += [f"{u} {r}" for u, r in {**absent, **retry}.items()]
        if not problems:
            return 0, [*lines, DONE]
        listed = [PROBLEM.format(problem=p) for p in problems]
        if not written and not absent:  # every chain unreadable or failed: nothing on file, a rerun may succeed
            return 1, [*lines, *listed, NOTHING.format(reasons="; ".join(problems))]
        return 1, [*lines, *listed, WITH_PROBLEMS.format(problems="; ".join(problems))]

    def _refusal(self, day: date, now: datetime, live: bool) -> str | None:
        if not live:
            return HAND_RUN
        if self.live_from is None or day < self.live_from:
            return NOT_LIVE.format(day=day, live_from=self.live_from)
        if day != now.date():
            return NOT_TODAY.format(day=day, today=now.date())
        return None if self.calendar.session_kind(day) == SESSION_REGULAR else NOT_TRADING  # A1: regular sessions
