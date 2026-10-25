"""The live daily record (section 7), run by O1's `price_distribution` step after the card, which alone passes
`--live`. One file per underlying per day; the command never alerts itself: O1's `Alerted` sends the one alert for a
failed or refused step.

- not live (no `--live`, no `daily.live_from.price_distribution`, before it, or not today): `nothing written: ...`,
  exit 0;
- a closed day: `not a trading day`, exit 0;
- a day already in Drive: never rebuilt (its `made_at` would change the bytes); the same bytes are put again, which
  restores a missing receipt, and the line says `already recorded`; its stored problems (a `missing` record
  included) count again, so a rerun of a problem day still fails (judge 310);
- no chain captured for any underlying: `nothing written: ...`, exit 0 (O1 records `refused`, one alert);
- a chain recorded but unreadable (Drive down) or a build that fails: no file for that underlying, so a rerun can
  still record it; with any other problem, every other file is written (a chain not captured as a `missing` record),
  one line per problem, last line `written with problems: ...`, exit 1 (O1 records `failed`, one alert, and commits
  the receipts);
- a later expiry too thin to value (`thin_expiry.py`): kept in the record's problems, named in a `note:` line, and
  not a failure on its own."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import date, datetime

from ..constants import SESSION_REGULAR, SESSION_SPECIAL
from ..research_data.calendar import SessionCalendar
from .build import DayBuilder, missing_record
from .chain import ChainSource
from .constants import LIVE
from .folders import live_path
from .records import Stamp, encode
from .sources import ChainUnavailable
from .store import DistributionStore
from .thin_expiry import thin_problems

NOT_LIVE = "nothing written: not live on {day} (config.yaml daily.live_from.price_distribution: {live_from})"
HAND_RUN = "nothing written: only O1's daily step writes live rows (--live); past days go through `pricedist backfill`"
NOT_TODAY = "nothing written: {day} is not today ({today}); past days go through `pricedist backfill`"
NOT_TRADING = "not a trading day"
NO_CHAIN = "no canonical 3 pm chain"
NOTHING = "nothing written: {reasons}"
NO_CHAIN_ANYWHERE = "nothing written: no 3 pm chain for any underlying ({reasons})"
BUILD_FAILED = "build failed ({kind}): {error}"
ALREADY = "{underlying}: already recorded"
ALREADY_WITH_PROBLEMS = "{underlying}: already recorded with {problems} problems"
RECORDED = "{underlying}: recorded ({problems} problems)"
PROBLEM = "problem: {problem}"
NOTE = "note: {note} (no forecast for that expiry)"
WITH_PROBLEMS = "written with problems: {problems}"
DONE = "recorded"
RECORDED_KINDS = (SESSION_REGULAR, SESSION_SPECIAL)


class LiveRecorder:
    def __init__(self, source: ChainSource, builder: DayBuilder, store: DistributionStore, calendar: SessionCalendar,
                 underlyings: Sequence[str], live_from: date | None, now: Callable[[], datetime]):  # fmt: skip
        self.source, self.builder, self.store, self.calendar = source, builder, store, calendar
        self.underlyings, self.live_from, self.now = tuple(underlyings), live_from, now

    def record(self, day: date, live: bool = True) -> tuple[int, list[str]]:
        now = self.now()
        refusal = self._refusal(day, now, live)
        if refusal:
            return 0, [refusal]
        lines, problems, absent, retry, notes = [], [], {}, {}, []
        for underlying in self.underlyings:
            path = live_path(underlying, day)
            existing = self.store.get(path)
            if existing is not None:
                self.store.put(path, existing)
                stored_record = json.loads(existing)
                stored = stored_record.get("problems") or []  # a rerun never turns a problem day into ok
                self._sort(underlying, stored_record, stored, problems, notes)
                line = ALREADY_WITH_PROBLEMS if stored else ALREADY
                lines.append(line.format(underlying=underlying, problems=len(stored)))
                continue
            try:
                chain = self.source.chain(underlying, day)
            except ChainUnavailable as error:
                retry[underlying] = str(error)
                continue
            if chain is None:
                absent[underlying] = NO_CHAIN
                continue
            try:
                record = self.builder.build(chain, LIVE, now.isoformat())
            except (ValueError, ArithmeticError) as error:  # a refused row, a NaN: never lose the other underlyings
                retry[underlying] = BUILD_FAILED.format(kind=type(error).__name__, error=error)
                continue
            self.store.put(path, encode(record))
            lines.append(RECORDED.format(underlying=underlying, problems=len(record["problems"])))
            self._sort(underlying, record, record["problems"], problems, notes)
        if len(absent) == len(self.underlyings):
            return 0, [NO_CHAIN_ANYWHERE.format(reasons="; ".join(f"{u}: {r}" for u, r in absent.items()))]
        stamp = Stamp(LIVE, self.builder.method, "", now.isoformat())
        for underlying, reason in absent.items():
            self.store.put(live_path(underlying, day), encode(missing_record(underlying, day, reason, stamp)))
        problems += [f"{u} {r}" for u, r in {**absent, **retry}.items()]
        noted = [NOTE.format(note=n) for n in notes]
        if not problems:
            return 0, [*lines, *noted, DONE]
        listed = [PROBLEM.format(problem=p) for p in problems]
        if not lines and not absent:  # every chain unreadable or failed: nothing written, and a rerun may succeed
            return 1, [*listed, NOTHING.format(reasons="; ".join(problems))]
        return 1, [*lines, *noted, *listed, WITH_PROBLEMS.format(problems="; ".join(problems))]

    @staticmethod
    def _sort(underlying: str, record: dict, found: list[str], problems: list[str], notes: list[str]) -> None:
        thin = thin_problems(record)
        problems += [f"{underlying} {p}" for p in found if p not in thin]
        notes += [f"{underlying} {p}" for p in found if p in thin]

    def _refusal(self, day: date, now: datetime, live: bool) -> str | None:
        if not live:
            return HAND_RUN
        if self.live_from is None or day < self.live_from:
            return NOT_LIVE.format(day=day, live_from=self.live_from)
        if day != now.date():
            return NOT_TODAY.format(day=day, today=now.date())
        return None if self.calendar.session_kind(day) in RECORDED_KINDS else NOT_TRADING
