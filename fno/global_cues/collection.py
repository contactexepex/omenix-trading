"""What a cue's download or archived copy yields (story A17): its values with the copy's SHA-256, or why nothing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .source import CueValue, GlobalCueSource

# a file that is not the publisher's layout: a short row (IndexError) or an impossible timestamp (OverflowError) too
UNREADABLE = (ValueError, KeyError, TypeError, IndexError, ArithmeticError)


@dataclass(frozen=True)
class SourcedValue:
    value: CueValue
    source_sha256: str


@dataclass
class Collection:
    cue: str
    fetched_at: datetime
    values: list[SourcedValue] = field(default_factory=list)
    failure: str = ""  # why nothing was saved; empty when every file was archived
    skipped: str = ""  # why nothing was downloaded although nothing failed (the once-a-day rule)


def final_values(source: GlobalCueSource, values: list[CueValue], seen_at: datetime) -> list[CueValue]:
    """Drops a value not yet final when its file was fetched: a US index history read during the US session may hold
    the day's price so far, which must never become a row (its source says so with `may_hold_unfinished`)."""
    if not source.may_hold_unfinished:
        return values
    return [v for v in values if source.available_at(v.value_date) < seen_at]
