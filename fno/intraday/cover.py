"""Every mark is taken by two fires (story A16i). The routine's prompt ends a fire at (H+2):05, so a mark at H+1:15,
:30 or :45 had exactly one fire; on 23 Oct the 13:52 fire never ran and 14:15, 14:30 and 14:45 were lost, which voided
the day's realised variance. The recorder itself therefore runs one hour past the `--until` it is given, up to the
session's end; the claims (one taker per mark) keep the extra fire from taking a mark twice. A fire killed early
(a session limit) leaves the cover as it was before: the first hour is still its own."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

EXTRA_COVER = timedelta(hours=1)
SESSION_END = time(15, 35)


def covered_until(until: time) -> time:
    """`until` plus the extra hour, never past the session's end (a later `until` is the caller's own choice)."""
    if until >= SESSION_END:
        return until
    extended = datetime.combine(date.min, until) + EXTRA_COVER
    return min(extended.time(), SESSION_END)
