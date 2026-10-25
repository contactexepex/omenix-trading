"""Entry conditions as small named features, each with a declared availability time (story B1).

A feature's `known_at(decision_day)` is the moment its value may be computed: data available after it must not change
the value (proved by the look-ahead harness in tests/research_engine/lookahead.py). F1-F3 are daily-close features:
known at the decision day's close, so valid for close-proxy research only; a 15:00 live version is a different
feature (story B7). A feature returns `None` when its inputs are missing, never a guess; runners treat `None` as
"condition not met". Times are IST, without a time zone.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time

from ..constants import SESSION_CLOSE_TIME, SESSION_MUHURAT
from ..research_data.events import Event
from ..research_data.panel_reader import NiftyPanel
from ..research_data.quote_snapshots import CutoffSnapshot

END_OF_DAY = time(23, 59, 59)  # muhurat sessions trade in the evening, at hours that change every year

FeatureValue = float | bool | None


@dataclass(frozen=True)
class ResearchData:
    """Everything a feature may read: the NIFTY panel (story A3), the events calendar (story A6) and, for live
    features, the 3 pm quote snapshots (story A4). All are inputs the look-ahead harness changes after the cutoff, so
    a feature gets nothing else."""

    panel: NiftyPanel
    events: tuple[Event, ...]
    snapshots: Mapping[date, CutoffSnapshot] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionContext:
    """The cycle being decided (story B2's dates): its monthly expiry, entry day and exit day."""

    expiry: date
    entry_day: date
    exit_day: date


def available_at(day: date, session: str) -> datetime:
    """When a session's closing data exists: its close for regular and special sessions, the end of the day for the
    evening muhurat session."""
    return datetime.combine(day, END_OF_DAY if session == SESSION_MUHURAT else SESSION_CLOSE_TIME)


class Feature(ABC):
    name: str

    def known_at(self, decision_day: date) -> datetime:
        """Daily-close features are known at the decision day's close; a live feature overrides this (story B7)."""
        return datetime.combine(decision_day, SESSION_CLOSE_TIME)

    @abstractmethod
    def value(self, data: ResearchData, decision_day: date, context: DecisionContext) -> FeatureValue:
        """The feature on the decision day, from data available by `known_at`; `None` when inputs are missing."""
