"""The A16h subscription-limit ramp (judge 499 addenda 2-4): 50, 500, 1,000, 1,500, 2,000, 3,000. A step is refused
when a call raises (not a 429, which stops the run at once) or the feed creates fewer topics than asked; a refused
batch is released at once. After the close, a refusal at 50 twice means a closed market; between marks, a first
refusal is a limit. Once 50 is accepted, a refused step is a limit, and the ramp halves its way down to it."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from .feed_universe import FeedInstrument

RAMP_STEPS = (50, 500, 1000, 1500, 2000, 3000)
RESOLUTION = 50  # the limit is pinned to within 50 subscriptions
STEP_SECONDS = 45
CLOSED = "closed market (refused at 50, twice)"
LIMIT = "subscription limit: {low} accepted, {high} refused"
NO_LIMIT = "no limit up to {top}"
HELD = "ramp: {count} subscriptions held"


class Ramp:
    def __init__(self, probe, after_close: bool):
        self.probe, self.after_close = probe, after_close

    def run(self, instruments: Sequence[FeedInstrument], end: datetime, outcome) -> None:
        low = 0
        for target in RAMP_STEPS:
            if self.probe.clock() >= end:
                return
            if self._take(instruments, low, target, end, outcome):
                low = target
                continue
            if target == RAMP_STEPS[0]:
                if self.after_close and self._take(instruments, low, target, end, outcome):
                    low = target
                    continue
                outcome.lines.append(CLOSED if self.after_close else LIMIT.format(low=0, high=target))
                return
            outcome.lines.append(LIMIT.format(**self._halve(instruments, low, target, end, outcome)))
            return
        outcome.lines.append(NO_LIMIT.format(top=RAMP_STEPS[-1]))

    def _halve(self, instruments, low: int, high: int, end: datetime, outcome) -> dict[str, int]:
        """The last accepted and the first refused count, narrowed to within RESOLUTION of each other."""
        while high - low > RESOLUTION and self.probe.clock() < end:
            middle = low + (high - low) // 2
            if self._take(instruments, low, middle, end, outcome):
                low = middle
            else:
                high = middle
        return {"low": low, "high": high}

    def _take(self, instruments, low: int, target: int, end: datetime, outcome) -> bool:
        """Adds instruments [low, target); True when every topic was created and the feed still answers."""
        batch = list(instruments[low:target])
        try:
            created = self.probe.subscribe(batch, outcome)
            self.probe.wait(STEP_SECONDS, end)
            self.probe.feed.get_ltp()  # a dropped subscription set shows here as a raised error
            accepted = created == len(batch)
        except Exception as error:
            if self.probe.rate_limited(error):
                raise  # a 429 stops the whole run
            accepted = False
        if not accepted:
            outcome.lines += self.probe.release(batch)
            return False
        outcome.reached = target
        outcome.lines.append(HELD.format(count=target))
        return True
