"""The 15:45 report's text (story FL1-1). Each report takes up, for the last `LOOKBACK_SESSIONS` regular sessions, every
target day an earlier report has not covered yet (judge 422): the seal check of every day up to today, and the match
of every earlier day whose official close is archived. A day the routine missed, or whose close was archived late, is
so covered by a later report, never skipped silently; one older than the window is left to the scoreboard. The
window starts no earlier than the lab's own first live day (the report covers only its own days); which forecasts are
expected at all is `MatchSection`'s rule (from G13b's first live day)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from .constants import HEADER, ISSUE_CLOSE, LOOKBACK_SESSIONS, NOT_ARCHIVED, UNDERLYINGS
from .match import MatchSection, next_ranges
from .ranges import RangeSource
from .scoreboard import scoreboard_lines, trust_line
from .written import WrittenReport, key


class Sections(ABC):
    """More report lines (FL1-1b's contract tracking joins here), each section with its alerts."""

    @abstractmethod
    def lines(self, day: date) -> tuple[list[str], list[str]]: ...


class CloseReport:
    def __init__(self, forecasts: RangeSource, match: MatchSection, first_day: date | None = None,
                 extra: tuple[Sections, ...] = (), underlyings: tuple[str, ...] = UNDERLYINGS):  # fmt: skip
        self.forecasts, self.match, self.first_day = forecasts, match, first_day
        self.extra, self.underlyings = extra, underlyings

    def _window(self, day: date) -> list[date]:
        days = self.match.sessions.window(day, LOOKBACK_SESSIONS)
        return [d for d in days if self.first_day is None or d >= self.first_day]

    def build(self, day: date, now: datetime, earlier: Callable[[date], WrittenReport | None]) -> WrittenReport:
        window = self._window(day)
        before = [w for w in (earlier(d) for d in window if d < day) if w is not None]
        draft = _Draft([HEADER.format(day=day)])
        for underlying in self.underlyings:
            self._check_seals(draft, underlying, window, {k for w in before for k in w.checked})
            self._match(draft, underlying, [d for d in window if d < day], {k for w in before for k in w.matched})
        for underlying in self.underlyings:
            draft.add(next_ranges(underlying, self.forecasts.sealed(underlying, day, ISSUE_CLOSE), now))
        for underlying in self.underlyings:
            draft.add([f"{underlying}:", *scoreboard_lines(self.forecasts.history(underlying, day))])
        for section in self.extra:
            draft.add(*section.lines(day))
        draft.add([trust_line(self.forecasts, self.underlyings, day)])
        return draft.written()

    def _check_seals(self, draft: _Draft, underlying: str, window: list[date], done: set[str]) -> None:
        for target in (d for d in window if key(underlying, d) not in done):
            draft.add(*self.match.seal_lines(underlying, target))
            draft.checked.append(key(underlying, target))

    def _match(self, draft: _Draft, underlying: str, targets: list[date], done: set[str]) -> None:
        for target in (d for d in targets if key(underlying, d) not in done):
            found = self.match.match_lines(underlying, target)
            lines, complete = found or ([NOT_ARCHIVED.format(underlying=underlying, target=target)], False)
            draft.add(lines)
            if complete:
                draft.matched.append(key(underlying, target))


@dataclass
class _Draft:
    lines: list[str]
    alerts: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    matched: list[str] = field(default_factory=list)

    def add(self, lines: list[str], alerts: list[str] = ()) -> None:
        self.lines += ["", *lines]
        self.alerts += alerts

    def written(self) -> WrittenReport:
        return WrittenReport("\n".join(self.lines) + "\n", tuple(self.alerts), tuple(self.checked), tuple(self.matched))
