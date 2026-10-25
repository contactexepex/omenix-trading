"""The versions' evidence (story REC1b, section 2): which versions the recommender rates and their counted forward
sessions. School driver versions are the registered `school:` rows of D6; a session counts for one when a sealed
15:00 decision of it on an open road is counted by MS-P1h's `CountingRule`, and its time is GitHub's push receipt of
the seal's commit (judge 620.2 m2; unknown: it does not count). The desk is rated as its book. A playbook version at
`paper` needs its own evidence reader, which is not built: it fails loudly rather than being rated by a guess. The
frozen reports (P2 and rung 3's) and RM1's eligibility have no reader until those reports exist, so none is named."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta

from ..books.version_registry import SCHOOL_BOOK_PREFIX
from ..constants import BOOK1_RULES
from ..school.constants import SLOT_1500, Outcome, RecordKind
from ..school.contracts.records import DecisionRecord
from ..school.contracts.seal import StaleSeal
from ..school.registration.counting import CountCandidate, CountingRule
from .constants import OutcomeSource
from .ports import EligibilityPort, EvidencePort, InputFailed
from .rungs import EvidenceReports, ForwardOutcome
from .school_source import SealedDecisions

INVALID = frozenset({Outcome.ROAD_CLOSED, Outcome.UNAVAILABLE})  # no valid session on a road that was not open
DESK_NOT_BUILT = "playbook version(s) at paper ({names}): the desk's evidence reader is not built (REC1b)"


class RecommenderEvidence(EvidencePort):
    def __init__(self, school_versions: Callable[[], Iterable[str]], desk_at_paper: Callable[[], Iterable[str]],
                 first_counted: date | None, sessions: Callable[[date, date], Iterable[date]],
                 dashcam: SealedDecisions, counting: CountingRule,
                 receipt_of: Callable[[str], datetime | None]):  # fmt: skip
        """`sessions(a, b)`: the NSE sessions from a to b, both included; `counting`: MS-P1h's `CountingRule`;
        `receipt_of(commit)`: GitHub's push receipt of a commit, None when GitHub cannot answer."""
        self.school_versions, self.desk_at_paper = school_versions, desk_at_paper
        self.first_counted, self.sessions, self.dashcam = first_counted, sessions, dashcam
        self.counting, self.receipt_of = counting, receipt_of

    def versions(self, day: date) -> tuple[str, ...]:
        if paper := sorted(self.desk_at_paper()):
            raise InputFailed(DESK_NOT_BUILT.format(names=", ".join(paper)))
        return (BOOK1_RULES, *sorted(v for v in self.school_versions() if v.startswith(SCHOOL_BOOK_PREFIX)))

    def outcomes(self, day: date, made_at: datetime) -> tuple[ForwardOutcome, ...]:
        if self.first_counted is None or self.first_counted >= day:
            return ()  # nothing can count before the first counted session (MS-P1h)
        found = []
        for session in self.sessions(self.first_counted, day - timedelta(days=1)):
            seal = self.dashcam.find(session, SLOT_1500, RecordKind.DECISIONS)
            if seal is not None:
                receipt = self.receipt_of(seal.commit)
                found += [self._outcome(r, seal.commit, receipt) for r in self._read(seal)]
        return tuple(found)

    def reports(self, version: str) -> EvidenceReports:
        return EvidenceReports()

    def _read(self, seal) -> list[DecisionRecord]:
        try:
            return [r for r in self.dashcam.read(seal) if isinstance(r, DecisionRecord)]
        except (
            StaleSeal,
            ValueError,
            OSError,
        ) as damaged:  # an unreadable seal is an input failure, never fewer sessions
            raise InputFailed(f"{seal.path}: {type(damaged).__name__}") from None

    def _outcome(self, record: DecisionRecord, commit: str, receipt: datetime | None) -> ForwardOutcome:
        decision = record.decision
        candidate = CountCandidate(record.session, record.road, decision.driver_id, record.card_sha256, commit)
        counted = self.counting.verdict(candidate).counted and decision.outcome not in INVALID
        return ForwardOutcome(SCHOOL_BOOK_PREFIX + decision.driver_id, record.session, OutcomeSource.FORWARD,
                              counted, receipt)  # fmt: skip


class NoEligibility(EligibilityPort):
    """RM1 names no version eligible until its report exists (no version can be at rung 3 before P2 either)."""

    def eligible(self, day: date) -> frozenset[str]:
        return frozenset()
