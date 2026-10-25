"""Protocol v4's capture as a quote part of the daily run (story G10 completion, criteria 1-2): A4e's named window
(`quotes record --window v4`, 14:32-14:40 since 25 Oct), unchanged, opened with the 3 pm parts at the run's start and
started at 14:29 (O1's margin before the window), waiting inside A4e's recorder for 14:32. Its times and dataset
come from A4e's window in `config.yaml`, never copied; it is live from `daily.live_from.v4_pack` and commits its own
files as soon as it ends (it shares none with NIFTY's 14:55 part)."""

from __future__ import annotations

from datetime import date, datetime

from ..constants import V4_PACK_LIVE_KEY
from ..quotes.recorder import DATASET, earliest_waiting_moment
from ..quotes.window import QuoteWindow
from .quote_parts import START_MARGIN, QuotePart

ANY_DAY = date(2026, 1, 1)  # the limit is a time of day; a real day keeps a 30-minute wait clear of `date.min`

V4_PART = "v4"
V4_STEM = "nifty"  # A4e's named window records NIFTY under A4's own stem, in its own dataset


def v4_quotes(window: QuoteWindow) -> str:
    """The pathspec of the window's own dataset folder: its sidecars and canonical markers (raw rows: Drive only)."""
    return f":(glob)research/data/quotes/{window.dataset(DATASET)}/**"


def v4_part(window: QuoteWindow) -> QuotePart:
    return QuotePart(
        V4_PART,
        ("quotes", "record", "--window", window.name),
        (v4_quotes(window),),
        not_before=_shortly_before(window),
        canonicals=((window.dataset(DATASET), V4_STEM),),
        window_end=window.end,
        live_key=V4_PACK_LIVE_KEY,
        apart=True,
    )


def _shortly_before(window: QuoteWindow):
    """O1's margin before the window's start, never earlier than A4's one early-limit rule (`earliest_waiting_moment`)
    with the window's own wait (A4e's `max_early_wait_minutes`, 30 in `config.yaml`) plus O1's margin: the recorder then
    waits minutes, not half an hour (a rehearsal runs at real speed while a recorder runs, REH1), and never says "too
    early" whatever the window's wait (self-review: the default 20 minutes would not be this window's)."""
    shortly = (datetime.combine(date.min, window.start) - START_MARGIN).time()
    limit = earliest_waiting_moment(ANY_DAY, window.start, window.max_early_wait_seconds) + START_MARGIN
    return max(shortly, limit.time())
