"""The morning's confirmation (story FL1-1d): each evening checks today's forecast on NSE's close from its index list,
before NSE's official close file exists (23:20 IST). The next morning compares each evening verdict with the official
close, through G13b's official closes (`Outcomes`). It says "confirmed" when the close and the verdict agree, notes a
different close with the same verdict, and gives a correction line plus one #fno-desk alert when the verdict
changes. A verdict whose official close is not archived yet is taken up by a later morning, within
`LOOKBACK_SESSIONS`; the morning's record keeps what it confirmed (`matched`), so nothing is confirmed twice."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from .constants import LOOKBACK_SESSIONS
from .ranges import Outcomes
from .sessions import RegularSessions
from .written import Verdict, WrittenReport, key

SAME = 0.01  # points: NSE's two sources agree to the paisa on 21 Oct (some evidence: one day)
CONFIRMED = "{underlying} {day:%a %d %b}: the evening's check stands (official close {close:,.2f})"
OTHER_CLOSE = (
    "{underlying} {day:%a %d %b}: official close {official:,.2f}, not {close:,.2f} as read in the evening; the verdict "
    "stands"
)
CORRECTED = (
    "{underlying} {day:%a %d %b}: CORRECTION: the official close {official:,.2f} (read {close:,.2f} in the evening) "
    "makes it {now}, not {was}"
)
NOT_YET = "{underlying} {day:%a %d %b}: the official close is not archived yet; confirmed in a later morning"
WORDS = {(True, True): "Correct", (False, True): "Close call", (False, False): "Missed"}


@dataclass(frozen=True)
class Confirmed:
    lines: tuple[str, ...]
    alerts: tuple[str, ...]
    keys: tuple[str, ...]  # the verdicts settled this morning (none is confirmed twice)


class Confirmation:
    def __init__(self, evenings: Callable[[date], WrittenReport | None],
                 mornings: Callable[[date], WrittenReport | None], closes: Outcomes,
                 sessions: RegularSessions):  # fmt: skip
        self.evenings, self.mornings, self.closes, self.sessions = evenings, mornings, closes, sessions

    def confirm(self, day: date) -> Confirmed:
        earlier = [d for d in self.sessions.window(day, LOOKBACK_SESSIONS) if d < day]
        done = {k for d in earlier for w in [self.mornings(d)] if w is not None for k in w.matched}
        lines, alerts, keys = [], [], []
        for evening in (self.evenings(d) for d in earlier):
            for verdict in evening.verdicts if evening is not None else ():
                if key(verdict.underlying, verdict.day) in done:
                    continue
                line, alert, settled = self._one(verdict)
                lines.append(line)
                alerts += [alert] if alert else []
                keys += [key(verdict.underlying, verdict.day)] if settled else []
        return Confirmed(tuple(lines), tuple(alerts), tuple(keys))

    def _one(self, v: Verdict) -> tuple[str, str | None, bool]:
        """(the line, its alert or None, settled: False only while the official close is not archived)."""
        official = self.closes.close(v.underlying, v.day)
        if official is None:
            return NOT_YET.format(underlying=v.underlying, day=v.day), None, False
        now, was = v.inside(official), (v.inside_50, v.inside_90)
        if now != was:
            line = CORRECTED.format(underlying=v.underlying, day=v.day, official=official, close=v.close,
                                    now=WORDS[now], was=WORDS[was])  # fmt: skip
            return line, line, True
        if abs(official - v.close) > SAME:
            return OTHER_CLOSE.format(underlying=v.underlying, day=v.day, official=official, close=v.close), None, True
        return CONFIRMED.format(underlying=v.underlying, day=v.day, close=official), None, True
