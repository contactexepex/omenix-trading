"""Story G11 C13's late go-live (judge 586 F1): the AI slots' misses count from their registered `effective_start`,
whatever day the owner sets `daily.live_from.ai_books_v4` to. So collect starts at the earliest AI start (the
sessions before go-live are `not_fired`, never gaps that would stop G8's looks), and `ai fire` says each day how
many such sessions there are."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ..constants import V4_SLOT_AI, V4_SLOT_HYBRID
from ..forecast_scoring.v4.records import SlotRegistry

AI_SLOTS = (V4_SLOT_HYBRID, V4_SLOT_AI)
BEFORE_GO_LIVE = "before the AI books' v4 go-live ({live_from}): not fired, a miss"
MISSED = (
    "{count} AI session(s) from the slots' start {start} fell before the go-live date {live_from}: each with a "
    "released pack is a not_fired miss (a system_late day is excused)"
)


def earliest_ai_start(registry: SlotRegistry) -> date | None:
    starts = [r.effective_start for (_, slot), r in registry.registered().items() if slot in AI_SLOTS]
    return min(starts, default=None)


def first_collected_day(registry: SlotRegistry, live_from: date | None) -> date | None:
    """The first session collect looks at: the earlier of the go-live date and the AI slots' start."""
    days = [d for d in (live_from, earliest_ai_start(registry)) if d is not None]
    return min(days, default=None)


def missed_before_go_live(registry: SlotRegistry, live_from: date | None, today: date,
                          sessions: Callable[[date, date], list[date]]) -> str:  # fmt: skip
    """The day's line on those misses, or '' when there are none."""
    start = earliest_ai_start(registry)
    if start is None or (live_from is not None and start >= live_from):
        return ""
    last = today if live_from is None else min(today, live_from)
    missed = [d for d in sessions(start, last) if live_from is None or d < live_from]
    shown = "not set" if live_from is None else live_from
    return MISSED.format(count=len(missed), start=start, live_from=shown) if missed else ""
