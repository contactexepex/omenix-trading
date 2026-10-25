"""What the recommender reads (story REC1b), one port per source of facts, each with its adapter wired in
`fno/recommend/wiring.py`. A port that cannot answer raises `InputFailed`; the gathering turns that into
`data_check_failed`, never into a pass or an empty answer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from .constants import CandidateSourceName
from .contracts import CandidateSource
from .refs import RecordRef
from .rungs import EvidenceReports, ForwardOutcome


class InputFailed(Exception):
    """An input could not be read, or its hash did not match: the day's answer is data_check_failed."""


class DataDisagrees(InputFailed):
    """The records were read and disagree (two live outcomes, an orphan correction, an untraded decision with an
    outcome): rereading cannot change them, so the check is final at once (judge 658.1 m1)."""


def open_run_log(root, day: date):
    """The day's run log; a log that does not read is an input failure, never an empty day."""
    from ..desk.run_log import RunLog

    try:
        return RunLog.open(root, day)
    except (OSError, ValueError, KeyError) as bad:
        raise InputFailed(f"the run log of {day} does not read ({type(bad).__name__})") from None


@dataclass(frozen=True)
class SeenDecision:
    """One decision of the day as its source sealed it: the version, where it lies, whether it traded."""

    version: str
    decision: RecordRef
    traded: bool


@dataclass(frozen=True)
class SourceReading:
    source: CandidateSource
    decisions: tuple[SeenDecision, ...]  # empty whenever the source is unavailable
    used: tuple[RecordRef, ...]  # the records read to know it, for the record's inputs


@dataclass(frozen=True)
class DayConditions:
    step_problems: bool
    quote_gate_failed: bool
    weather_red: bool
    used: tuple[RecordRef, ...]


class CandidateSourcePort(ABC):
    name: CandidateSourceName  # the source this port reads

    @abstractmethod
    def read(self, day: date) -> SourceReading:
        """The source's decisions of `day`, or the source marked unavailable with its step's status."""


class EvidencePort(ABC):
    @abstractmethod
    def versions(self, day: date) -> tuple[str, ...]:
        """Every version the recommender rates on `day`."""

    @abstractmethod
    def outcomes(self, day: date, made_at: datetime) -> tuple[ForwardOutcome, ...]:
        """The versions' forward sessions with their counting verdicts and push receipts."""

    @abstractmethod
    def reports(self, version: str) -> EvidenceReports:
        """The frozen reports that passed for `version` (the P2 review, rung 3's three); none until they exist."""


class ConditionsPort(ABC):
    @abstractmethod
    def conditions(self, day: date) -> DayConditions: ...


class EligibilityPort(ABC):
    @abstractmethod
    def eligible(self, day: date) -> frozenset[str]:
        """The versions RM1's report names eligible on `day`; empty while no such report exists."""
