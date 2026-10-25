"""The live issue, run by O1's `premium_ranges` step right after G13's `price_distribution` (which alone writes the
day's 3 pm record G13d reads). G13's exit contract: not live or a hand run -> `nothing written: ...`, exit 0; a closed
day -> `not a trading day`; at or after 15:30 -> `nothing written: past the 15:30 seal` (O1's owner, 22 Oct:
never a late issue); an issued day is never rebuilt; no G13 record for an underlying -> a problem line, no
file, exit 1 (a rerun after G13's step can still issue). The command never alerts."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import date, datetime

from ..constants import SESSION_REGULAR
from ..price_distribution.folders import live_path as g13_live_path
from ..price_distribution.records import encode
from ..price_distribution.store import DistributionStore
from ..research_data.calendar import SessionCalendar
from .build import premium_record
from .constants import DEADLINE, ISSUE
from .folders import live_path

NOT_LIVE = "nothing written: not live on {day} (config.yaml daily.live_from.premium_ranges: {live_from})"
HAND_RUN = "nothing written: only O1's daily step writes live rows (--live)"
NOT_TODAY = "nothing written: {day} is not today ({today})"
NOT_TRADING = "not a trading day"
PAST_SEAL = "nothing written: past the {deadline} seal (now {now})"  # O1 records it refused and alerts once
NO_G13 = "{underlying}: no G13 3 pm record for {day}"
ALREADY = "{underlying}: already issued"
ISSUED = "{underlying}: issued ({rows} contracts ranged; not ranged {not_ranged})"
DONE, WITH_PROBLEMS = "issued", "written with problems: {problems}"


class PremiumIssuer:
    def __init__(self, store: DistributionStore, calendar: SessionCalendar, underlyings: Sequence[str],
                 live_from: date | None, now: Callable[[], datetime], method_sha256: str,
                 before: Callable[[date], list[str]] = lambda day: []):  # fmt: skip
        """`before(day)`: run first (the final seals of earlier issues); its lines are printed."""
        self.store, self.calendar, self.underlyings, self.live_from = store, calendar, tuple(underlyings), live_from
        self.now, self.method, self.before = now, method_sha256, before

    def issue(self, day: date, live: bool = True) -> tuple[int, list[str]]:
        now = self.now()
        refusal = self._refusal(day, now, live)
        if refusal:
            return 0, [refusal]
        lines, problems = list(self.before(day)), []
        for underlying in self.underlyings:
            path = live_path(underlying, day, ISSUE)
            existing = self.store.get(path)
            if existing is not None:
                self.store.put(path, existing)  # restores a missing receipt; same bytes, no change
                lines.append(ALREADY.format(underlying=underlying))
                continue
            g13 = self.store.get(g13_live_path(underlying, day))
            if g13 is None:
                problems.append(NO_G13.format(underlying=underlying, day=day))
                continue
            record = premium_record(json.loads(g13), self.calendar.next_session(day), self.method, now.isoformat())
            self.store.put(path, encode(record))
            lines.append(ISSUED.format(underlying=underlying, rows=len(record["rows"]),
                                       not_ranged=record["not_ranged"]))  # fmt: skip
        if problems:
            return 1, [*lines, *problems, WITH_PROBLEMS.format(problems="; ".join(problems))]
        return 0, [*lines, DONE]

    def _refusal(self, day: date, now: datetime, live: bool) -> str | None:
        if not live:
            return HAND_RUN
        if self.live_from is None or day < self.live_from:
            return NOT_LIVE.format(day=day, live_from=self.live_from)
        if day != now.date():
            return NOT_TODAY.format(day=day, today=now.date())
        if now.time() >= DEADLINE:  # issued after the seal's deadline it could never count
            return PAST_SEAL.format(deadline=DEADLINE.strftime("%H:%M"), now=now.strftime("%H:%M:%S"))
        return None if self.calendar.session_kind(day) == SESSION_REGULAR else NOT_TRADING
