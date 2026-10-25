"""Side-by-side check of two participant-OI release logs (story O6 criterion 1): the Claude routine's and the GitHub
Actions copy's, written by the same command on the same days. A day is the same output when both ran, both saw the
same file (SHA-256), and both measured it (seen absent first) within one check interval of each other, or neither
measured it."""

from __future__ import annotations

from datetime import date, timedelta

from ..constants import RELEASE_PRESENT
from .release_times import ReleaseCheck, first_seen_times

SAME, DIFFERENT, ONE_SIDE = "same", "DIFFERENT", "only one ran"
DAY_LINE = "{day}: routine {routine}; actions {actions}; {verdict}"
TOTAL_LINE = "{same} of {days} days the same; {different} different; {one_side} with only one run"


def _seen(checks: list[ReleaseCheck], day: date) -> tuple[str, str]:
    """(SHA-256 of the first present check, its time) for the day, or ('', the last outcome) if never present."""
    ordered = sorted((c for c in checks if c.day == day), key=lambda c: c.checked_at)
    present = next((c for c in ordered if c.outcome == RELEASE_PRESENT), None)
    if present is None:
        return "", ordered[-1].outcome if ordered else "no check"
    return present.sha256, f"{present.checked_at:%H:%M}"


class ReleaseLogComparison:
    def __init__(self, routine: list[ReleaseCheck], actions: list[ReleaseCheck], interval: timedelta):
        self.routine, self.actions, self.interval = routine, actions, interval
        self.measured = first_seen_times(routine), first_seen_times(actions)

    def lines(self) -> list[str]:
        days = sorted({c.day for c in self.routine} | {c.day for c in self.actions})
        lines, counts = [], {SAME: 0, DIFFERENT: 0, ONE_SIDE: 0}
        for day in days:
            (r_sha, r_at), (a_sha, a_at) = _seen(self.routine, day), _seen(self.actions, day)
            verdict = self._verdict(day, r_sha == a_sha)
            counts[verdict] += 1
            lines.append(DAY_LINE.format(day=day, routine=f"{r_at} {r_sha[:12]}", actions=f"{a_at} {a_sha[:12]}",
                                         verdict=verdict))  # fmt: skip
        total = TOTAL_LINE.format(
            same=counts[SAME], different=counts[DIFFERENT], one_side=counts[ONE_SIDE], days=len(days)
        )
        return [*lines, total]

    def _verdict(self, day: date, same_file: bool) -> str:
        if not any(c.day == day for c in self.routine) or not any(c.day == day for c in self.actions):
            return ONE_SIDE
        first_r, first_a = self.measured[0].get(day), self.measured[1].get(day)
        if (first_r is None) != (first_a is None):
            return DIFFERENT
        timing_agrees = first_r is None or abs(first_r - first_a) <= self.interval
        return SAME if same_file and timing_agrees else DIFFERENT
