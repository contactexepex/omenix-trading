"""The evening check of one recommended day (story REC1c): every candidate the recommendation fixed at decision time,
looked up in its sealed outcomes, each reported and summed; never a new search of the day's decisions, never a price.
A candidate that traded and has no outcome yet is open, so the day is not known yet; a candidate whose outcome
cannot be read fails the whole check, never a smaller total (judge 620 S3)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from .check_record import (
    CHECK_KIND,
    CHECK_SCHEMA_VERSION,
    NEVER_CLOSED,
    CandidateResult,
    CandidateState,
    CheckRecord,
    verdict_for,
)
from .constants import WINDOW_SESSIONS, SourceState
from .contracts import Candidate, Recommendation
from .ports import DataDisagrees

MISMATCH = "{key}: an untraded decision has a trade's outcome"


@dataclass(frozen=True)
class FoundOutcome:
    net: float  # rupees after every charge
    is_ticket: bool


class OutcomeLookup(ABC):
    @abstractmethod
    def outcome(self, candidate: Candidate, session: date, until: date) -> FoundOutcome | None:
        """The candidate's sealed closed outcome between its session and `until`, None while none is sealed; an
        unreadable outcome raises `InputFailed`."""

    @abstractmethod
    def ticket(self, candidate: Candidate, session: date) -> bool:
        """True when the candidate's sealed decision was a school ticket (a measurement, never a trade)."""


def check(record: Recommendation, record_sha256: str, checked_on: date, made_at: datetime, lookup: OutcomeLookup,
          last_check: bool) -> CheckRecord:  # fmt: skip
    """`last_check`: the window's last session; a candidate still open then is never closed (judge 658 S3)."""
    results = tuple(_result(c, record.session, checked_on, lookup) for c in record.candidates)
    unavailable = tuple(sorted(s.name.value for s in record.candidate_sources if s.state is SourceState.UNAVAILABLE))
    closed = [r.net for r in results if r.state is CandidateState.CLOSED]
    open_positions = sum(r.state is CandidateState.OPEN for r in results)
    problem = NEVER_CLOSED.format(sessions=WINDOW_SESSIONS) if open_positions and last_check else ""
    return CheckRecord(
        schema_version=CHECK_SCHEMA_VERSION, kind=CHECK_KIND, session=record.session, checked_on=checked_on,
        made_at=made_at, recommendation_sha256=record_sha256, results=results, closed_so_far=round(sum(closed), 2),
        open_positions=open_positions, unavailable_sources=unavailable, last_check=last_check, problem=problem,
        verdict=verdict_for(unavailable, open_positions, problem),
    )  # fmt: skip


def unreadable(session: date, checked_on: date, made_at: datetime, problem: str) -> CheckRecord:
    """The last check of a day whose inputs cannot be read: final and alerted, so no day leaves the window silently."""
    return CheckRecord(
        schema_version=CHECK_SCHEMA_VERSION, kind=CHECK_KIND, session=session, checked_on=checked_on, made_at=made_at,
        recommendation_sha256="", results=(), closed_so_far=0.0, open_positions=0, unavailable_sources=(),
        last_check=True, problem=problem, verdict=verdict_for((), 0, problem),
    )  # fmt: skip


def _result(candidate: Candidate, session: date, until: date, lookup: OutcomeLookup) -> CandidateResult:
    found = lookup.outcome(candidate, session, until)
    key = (candidate.version, candidate.decision.path)
    if found is not None and found.is_ticket:
        return CandidateResult(*key, CandidateState.TICKET, found.net)  # a ticket is never counted as a trade
    if candidate.traded:
        return CandidateResult(*key, CandidateState.CLOSED if found else CandidateState.OPEN, found and found.net)
    if found is not None:  # an untraded decision with a trade's outcome: the records disagree
        raise DataDisagrees(MISMATCH.format(key=candidate.decision.path))
    if lookup.ticket(candidate, session):  # an open ticket keeps the day open, so it is reported once it closes
        return CandidateResult(*key, CandidateState.OPEN, None)
    return CandidateResult(*key, CandidateState.NO_TRADE, None)
