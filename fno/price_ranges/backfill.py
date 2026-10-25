"""G13b's back-fill (part A7): each session of a range rebuilt from captured inputs. `backfill_eod` reads an end-of-day
chain (G13's panel for NIFTY, the bhavcopy for BANKNIFTY) on the `CLOSE` basis; `backfill_3pm` reads A4's and A4c's
chains on the `CAPTURE` basis. As G13's: one gzip file per run and underlying, named by method and content, so a
rerun is a no-op and new inputs go to a new path; stops before the first live day; never alerts; skipped days and
problem days counted by reason."""

from __future__ import annotations

import gzip
import hashlib
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import date

from ..constants import SESSION_REGULAR
from ..forecast_v4_rules.series import DayValue
from ..price_distribution.chain import ChainSource
from ..price_distribution.recorder import NO_CHAIN
from ..price_distribution.sources import ChainUnavailable
from ..research_data.calendar import CalendarError, SessionCalendar
from .build import CAPTURE, CLOSE, Basis, RangeBuilder
from .constants import BACKFILL_3PM, BACKFILL_EOD, ISSUE_1545
from .folders import backfill_path
from .records import encode

SCHEMA = "g13b_backfill_v1"
BASES = {BACKFILL_EOD: CLOSE, BACKFILL_3PM: CAPTURE}  # a back-fill label and its one basis; never `live`
WRONG_LABEL = "a back-fill is labelled backfill_eod (CLOSE basis) or backfill_3pm (CAPTURE basis), not {label}/{basis}"
STOPS = "back-fill stops before the first live day {live_from}"
WRITTEN = "{underlying} {label}: {days} days written to {path}"
NONE_WRITTEN = "{underlying} {label}: no day to write"
SKIPPED = "{underlying} {label}: {count} days skipped: {reason}"
PROBLEM_DAYS = "{underlying} {label}: {count} written days with: {reason}"


class RangeBackfill:
    def __init__(self, chains: ChainSource, builder: RangeBuilder, closes: Callable[[str], Sequence[DayValue]],
                 store, calendar: SessionCalendar, live_from: date | None):  # fmt: skip
        self.chains, self.builder, self.closes, self.store = chains, builder, closes, store
        self.calendar, self.live_from = calendar, live_from

    def run(self, label: str, basis: Basis, underlyings: Sequence[str], first: date, last: date) -> list[str]:
        if BASES.get(label) != basis:  # a back-fill is never counted as a sealed live day (judge 416)
            raise ValueError(WRONG_LABEL.format(label=label, basis=basis.name))
        lines = []
        if self.live_from is not None and last >= self.live_from:
            last = min(last, self.calendar.previous_session(self.live_from))
            lines.append(STOPS.format(live_from=self.live_from))
        days = [d for d in self.calendar.sessions(first, last) if self.calendar.session_kind(d) == SESSION_REGULAR]
        for underlying in underlyings:
            closes = self.closes(underlying)
            records, skipped, problems = [], Counter(), Counter()
            for day in days:
                record = self._day(underlying, day, closes, basis, label, skipped)
                if record is not None:
                    records.append(record)
                    problems.update(p.split(":")[0] for p in set(record["problems"]))
            lines += [SKIPPED.format(underlying=underlying, label=label, count=n, reason=r) for r, n in skipped.items()]
            lines += [PROBLEM_DAYS.format(underlying=underlying, label=label, count=n, reason=r)
                      for r, n in sorted(problems.items())]  # fmt: skip
            lines.append(self._write(label, underlying, first, last, records))
        return lines

    def _day(self, underlying: str, day: date, closes, basis: Basis, label: str, skipped: Counter) -> dict | None:
        try:
            chain = self.chains.chain(underlying, day)
        except ChainUnavailable as error:
            skipped[str(error)] += 1
            return None
        if chain is None:
            skipped[NO_CHAIN] += 1
            return None
        try:
            return self.builder.build(underlying, day, ISSUE_1545, chain, closes, basis, label, None)
        except (ValueError, ArithmeticError, CalendarError) as error:  # a refused row, a NaN: that day only
            skipped[f"build failed ({type(error).__name__}): {error}"] += 1
            return None

    def _write(self, label: str, underlying: str, first: date, last: date, records: list[dict]) -> str:
        if not records:
            return NONE_WRITTEN.format(underlying=underlying, label=label)
        payload = {"schema": SCHEMA, "label": label, "underlying": underlying, "method_sha256": self.builder.method,
                   "first": first.isoformat(), "last": last.isoformat(), "records": records}  # fmt: skip
        data = encode(payload)
        path = backfill_path(label, self.builder.method, underlying, first, last, hashlib.sha256(data).hexdigest())
        self.store.put(path, gzip.compress(data, mtime=0))
        return WRITTEN.format(underlying=underlying, label=label, days=len(records), path=path)
