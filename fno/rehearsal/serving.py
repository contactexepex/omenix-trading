"""How near the replay clock's now a recorded answer is served (story REH1, REH1g's gap G4).

- A scheduled read (A4h's closes, A16b's candles) is served the day's answer saved from `EARLIER` before now to
  `NEAREST` after it, the earliest of them (`is_near`): the day saved its answer seconds to minutes after it asked.
  When none was saved so near, it is served the latest answer of the same day saved before now (`scheduled_pick`,
  REH1q): a rehearsal's exercised steps can push a live read past the day's (21 Oct: `price_ranges`' ten exercised
  minutes moved the candle read from the day's 15:33:06 to 15:35:43, past its 15:33:11 answer), and the latest
  answer before now existed then.
- A paced read (A17e's cues, A22's pre-open parts, read every 30 s or one index after another) is served the day's copy
  nearest to now within `AROUND` either side, never the same copy twice and never one older than the last served
  (`ServedOnce`): each of the day's reads had its own copy, so a retry is never handed an earlier read's copy.

An answer saved before now is no look-ahead: it existed then. One saved after now is served only once the replay clock
reaches its time (each source waits). `EARLIER` and `AROUND` are a minute because a rehearsal's reads drift a few
seconds from the day's (DRY2: KOSPI's copy at 08:50:34, read at 08:50:40, was missed at 5 s)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import TypeVar

from ..models import IST

EARLIER = timedelta(seconds=60)
NEAREST = timedelta(minutes=10)
AROUND = timedelta(seconds=60)

Copy = TypeVar("Copy")


def is_near(now: datetime, saved: datetime) -> bool:
    return now - EARLIER <= saved <= now + NEAREST


def scheduled_pick(now: datetime, answers: Iterable[tuple[datetime, Copy]]) -> tuple[datetime, Copy] | None:
    """A scheduled read's answer: the earliest saved near now (the day's own read), else the latest saved before now
    on the same IST day (never a later day's, and never one saved after now from behind: ahead stays `NEAREST`)."""
    answers = list(answers)
    near = [(saved, copy) for saved, copy in answers if is_near(now, saved)]
    if near:
        return min(near, key=lambda found: found[0])
    day = now.astimezone(IST).date()
    before = [(saved, copy) for saved, copy in answers if saved <= now and saved.astimezone(IST).date() == day]
    return max(before, key=lambda found: found[0], default=None)


class ServedOnce:
    """One paced reader's copies (one pre-open part, one URL), served once each and in the day's order: a copy saved
    at or before the last one served is never served again, so the answers never go back in time."""

    def __init__(self):
        self._last: datetime | None = None

    def pick(self, now: datetime, copies: Iterable[tuple[datetime, Copy]]) -> tuple[datetime, Copy] | None:
        """The copy saved nearest to now within `AROUND` (the earlier of two equally near) and after the last one
        served, or None."""
        near = [(abs(saved - now), saved, copy) for saved, copy in copies
                if abs(saved - now) <= AROUND and (self._last is None or saved > self._last)]  # fmt: skip
        if not near:
            return None
        _, saved, copy = min(near, key=lambda found: found[:2])
        self._last = saved
        return saved, copy
