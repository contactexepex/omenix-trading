"""NIFTY's weekly contracts at 3 pm (story A4f; owner, 21 Oct 2026: "Weekly contracts"): the two nearest listed NIFTY
expiries that are not one of the day's two monthlies, recorded after the other indices in A4c's window and pace, in
their own dataset (stem `niftyweekly`, so NIFTY's `nifty_*` commit glob and the monthly readers never take them).
BANKNIFTY lists no weeklies since Nov 2024."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

WEEKLY_DATASET = "groww/derivatives/quote-snapshots-weekly"  # beside A4's dataset (recorder.DATASET); a test pins it
WEEKLY_STEM = "niftyweekly"
WEEKLY_NAME = "NIFTY weekly"  # the result line's and the alert's name
WEEKLY_EXPIRIES = 2  # the nearest weekly and the next (the owner's "and the next if cheap": about 75 s more)
NO_WEEKLY = "no NIFTY weekly expiry listed after today"


def nearest_weeklies(
    listed: Iterable[date], monthlies: Iterable[date], day: date, count: int = WEEKLY_EXPIRIES
) -> list:
    """The `count` nearest listed expiries after `day` that are not the monthlies. An expiry on the day itself is not
    taken: at about 15:05 it has minutes left and the next-session premium range (piece 2) cannot score it."""
    excluded = set(monthlies)
    return sorted(e for e in set(listed) if e > day and e not in excluded)[:count]
