"""The evening check's record (story REC1c, section 5 and its text amendment): one write-once file per checked day and
evening. It lists every candidate the recommendation fixed at decision time, never more or fewer, each with its
state and, once closed, its net after costs; the total covers closed trades only, and the verdict says whether the
day is known. A record whose parts disagree is refused when it is made, so no reader ever meets one."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from ..school.contracts.codec import CanonicalRecord
from .contracts import RecordRefused

CHECK_KIND = "recommendation_check"
CHECK_SCHEMA_VERSION = 1


class CandidateState(StrEnum):
    NO_TRADE = "no_trade"  # the candidate decided not to trade: it contributes zero
    OPEN = "open"  # traded, not closed yet: the day is not known yet
    CLOSED = "closed"  # traded and closed: its net after costs counts
    TICKET = "ticket"  # a school ticket: reported apart, never counted as a trade


class Verdict(StrEnum):
    NOT_KNOWN_YET = "not_known_yet"  # a listed candidate is still open: checked again
    COMPLETE = "complete"  # every listed candidate closed: final
    INCOMPLETE = "incomplete"  # all closed, but a source was unavailable at decision time: no full total; final
    DATA_CHECK_FAILED = "data_check_failed"  # never closed in the window, or an outcome unresolved: final, alerted


FINAL = frozenset({Verdict.COMPLETE, Verdict.INCOMPLETE, Verdict.DATA_CHECK_FAILED})
NEVER_CLOSED = "never closed in {sessions} sessions"


@dataclass(frozen=True)
class CandidateResult:
    version: str
    decision_path: str  # the candidate's key in the recommendation
    state: CandidateState
    net: float | None  # rupees after every charge; only for a closed trade or a closed ticket


@dataclass(frozen=True)
class CheckRecord(CanonicalRecord):
    schema_version: int
    kind: str
    session: date  # the recommendation's day
    checked_on: date
    made_at: datetime
    recommendation_sha256: str
    results: tuple[CandidateResult, ...]  # every listed candidate; empty only for a check that could not read them
    closed_so_far: float  # the sum over the trades closed so far (tickets apart); the day's total only when final
    open_positions: int
    unavailable_sources: tuple[str, ...]
    last_check: bool  # the check on the window's last session: whatever it finds is final
    problem: str  # why the check is data_check_failed; empty otherwise
    verdict: Verdict

    def __post_init__(self):
        if problems := _problems(self):
            raise RecordRefused("; ".join(problems))


def _problems(rec: CheckRecord) -> list[str]:
    closed = [r for r in rec.results if r.state is CandidateState.CLOSED]
    checks = (
        (type(rec.schema_version) is int and rec.schema_version == CHECK_SCHEMA_VERSION and rec.kind == CHECK_KIND,
         "not a check record v1"),
        (rec.made_at.utcoffset() == timedelta(0), "made_at is not a UTC time"),
        (rec.checked_on >= rec.session, "a check before its day"),
        (all((r.net is None) == (r.state in (CandidateState.NO_TRADE, CandidateState.OPEN)) for r in rec.results),
         "a net is given exactly for closed trades and tickets"),
        (rec.closed_so_far == round(sum(r.net for r in closed), 2), "closed so far is not the sum of closed trades"),
        (rec.open_positions == sum(r.state is CandidateState.OPEN for r in rec.results), "the open count is wrong"),
        (type(rec.last_check) is bool and isinstance(rec.problem, str), "last_check or problem has the wrong type"),
        (rec.verdict is verdict_for(rec.unavailable_sources, rec.open_positions, rec.problem), "a wrong verdict"),
        (bool(rec.results) or bool(rec.problem) or rec.open_positions == 0, "no results without a problem"),
        (not (rec.open_positions and rec.last_check) or bool(rec.problem), "open at the last check, no problem"),
        (list(rec.unavailable_sources) == sorted(set(rec.unavailable_sources)), "sources are not sorted or repeat"),
    )  # fmt: skip
    return [problem for ok, problem in checks if not ok]


def verdict_for(unavailable: tuple[str, ...], open_positions: int, problem: str) -> Verdict:
    """The one rule the check and its record both use (judge 658 S3): a problem first, then open trades, then an
    unavailable source; a day with an unavailable source is re-checked until its listed candidates have closed."""
    if problem:
        return Verdict.DATA_CHECK_FAILED
    if open_positions:
        return Verdict.NOT_KNOWN_YET
    return Verdict.INCOMPLETE if unavailable else Verdict.COMPLETE
