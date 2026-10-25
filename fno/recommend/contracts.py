"""The recommendation record (story REC1a, sections 1 and 5): one per NSE session, written once. It holds both answers,
the evidence each version had at decision time, and the day's candidate set fixed at decision time (judge 620 S3 and
620.1), so the evening check never chooses its candidates with hindsight. A record that breaks a rule is refused when
it is made, so no reader ever meets one."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from ..books.version_registry import SCHOOL_BOOK_PREFIX
from ..school.contracts.codec import CanonicalRecord
from .constants import (
    BLOCKS_REAL_MONEY,
    RECORD_KIND,
    RECORD_SCHEMA_VERSION,
    CandidateSourceName,
    EvidenceRung,
    NoTradeReason,
    PaperAnswer,
    RealMoneyAnswer,
    SourceState,
)
from .refs import RecordRef
from .rungs import VersionEvidence

SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
# While no version is established only these can be the reason (story section 1)
UNPROVEN_REASONS = frozenset({NoTradeReason.DATA_CHECK_FAILED, NoTradeReason.STEP_PROBLEMS,
                              NoTradeReason.NO_ESTABLISHED_VERSION})  # fmt: skip


class RecordRefused(ValueError):
    """A recommendation that breaks the story's rules, or bytes that do not read as one."""


@dataclass(frozen=True)
class Candidate:
    """One version's or control's decision of the day, as the recommendation saw it."""

    version: str
    rung: EvidenceRung
    decision: RecordRef
    traded: bool

    def __post_init__(self):
        if type(self.traded) is not bool:
            raise RecordRefused("a candidate's traded is not true or false")


@dataclass(frozen=True)
class CandidateSource:
    """One source of the day's candidates and whether it could be read; `step_status` says why it could not."""

    name: CandidateSourceName
    state: SourceState
    step_status: str | None

    def __post_init__(self):
        unavailable = self.state is SourceState.UNAVAILABLE
        if unavailable != (isinstance(self.step_status, str) and bool(self.step_status)):
            raise RecordRefused("an unavailable source names its step status, and only then")


@dataclass(frozen=True)
class Recommendation(CanonicalRecord):
    schema_version: int
    kind: str
    session: date
    made_at: datetime
    evidence_cutoff: datetime
    code_commit: str
    config_sha256: str
    rung_rule_sha256: str
    inputs: tuple[RecordRef, ...]
    versions: tuple[VersionEvidence, ...]
    candidates: tuple[Candidate, ...]
    candidate_sources: tuple[CandidateSource, ...]
    braked_versions: tuple[str, ...]  # held by their own drawdown brake or daily stop: never eligible (REC1c)
    real_money: RealMoneyAnswer
    eligible_version: str | None
    paper: PaperAnswer
    paper_trade: Candidate | None
    reason: NoTradeReason | None

    def __post_init__(self):
        if problems := _problems(self):
            raise RecordRefused("; ".join(problems))


def _problems(rec: Recommendation) -> list[str]:
    rungs = {v.version: v.rung for v in rec.versions}
    checks = (
        (_is_int(rec.schema_version, RECORD_SCHEMA_VERSION) and rec.kind == RECORD_KIND, "not a record v1"),
        (_is_utc(rec.made_at), "made_at is not a UTC time"),
        (rec.evidence_cutoff == rec.made_at and _is_utc(rec.evidence_cutoff), "evidence_cutoff is not made_at"),
        (COMMIT.fullmatch(rec.code_commit) is not None, "code_commit is not a commit id"),
        (all(_is_sha(h) for h in _hashes(rec)), "a SHA-256 is malformed"),
        (_sorted_unique([ref.path for ref in rec.inputs]), "inputs are not sorted by path or repeat one"),
        (_sorted_unique([v.version for v in rec.versions]), "versions are not sorted or repeat one"),
        (_sorted_unique(list(rec.braked_versions)), "braked versions are not sorted or repeat one"),
        (all(rungs.get(v) is EvidenceRung.ESTABLISHED for v in rec.braked_versions), "a braked version is not rung 3"),
        (_sorted_unique([_candidate_key(c) for c in rec.candidates]), "candidates are not sorted or repeat one"),
        (all(rungs.get(c.version) == c.rung for c in rec.candidates),
         "a candidate's rung is not its version's evidence rung"),
        ([s.name for s in rec.candidate_sources] == sorted(CandidateSourceName), "not one entry per candidate source"),
        (not (_unavailable(rec) & {source_of(c.version) for c in rec.candidates}),
         "a candidate comes from an unavailable source"),
        (_real_money_consistent(rec, rungs), "the real-money answer and its eligible version disagree"),
        (_paper_consistent(rec, rungs), "the paper answer, its trade and its reason disagree"),
    )  # fmt: skip
    return [problem for ok, problem in checks if not ok]


def _real_money_consistent(rec: Recommendation, rungs: dict[str, EvidenceRung]) -> bool:
    if rec.real_money is RealMoneyAnswer.DO_NOT_TRADE_REAL_MONEY:
        return rec.eligible_version is None
    proven = rungs.get(rec.eligible_version) is EvidenceRung.ESTABLISHED  # only a proven version, judge 620 S1
    clear_day = rec.reason not in BLOCKS_REAL_MONEY  # never on a day the paper answer is stopped by the day itself
    unbraked = rec.eligible_version not in rec.braked_versions  # orchestrator's ruling on judge 654.1's open point
    return proven and clear_day and unbraked and source_of(rec.eligible_version) not in _unavailable(rec)


def _paper_consistent(rec: Recommendation, rungs: dict[str, EvidenceRung]) -> bool:
    established = EvidenceRung.ESTABLISHED in rungs.values()
    unavailable = _unavailable(rec)
    if any(rung is EvidenceRung.ESTABLISHED and source_of(v) in unavailable for v, rung in rungs.items()):
        return rec.paper is PaperAnswer.NO_TRADE and rec.reason is NoTradeReason.DATA_CHECK_FAILED  # unread decisions
    if rec.paper is PaperAnswer.NO_TRADE:
        possible = set(NoTradeReason) - {NoTradeReason.NO_ESTABLISHED_VERSION} if established else UNPROVEN_REASONS
        return rec.paper_trade is None and rec.reason in possible
    trade = rec.paper_trade
    return (rec.reason is None and trade is not None and trade.traded and trade in rec.candidates
            and trade.rung is EvidenceRung.ESTABLISHED)  # fmt: skip


def source_of(version: str) -> CandidateSourceName:
    """A school driver version's candidates come from the school, every book's from the desk."""
    return CandidateSourceName.SCHOOL if version.startswith(SCHOOL_BOOK_PREFIX) else CandidateSourceName.DESK_BOOK1


def _unavailable(rec: Recommendation) -> set[CandidateSourceName]:
    return {s.name for s in rec.candidate_sources if s.state is SourceState.UNAVAILABLE}


def _hashes(rec: Recommendation) -> list[str]:
    refs = [*rec.inputs, *(c.decision for c in rec.candidates), *(r for v in rec.versions for r in v.reports.refs())]
    return [rec.config_sha256, rec.rung_rule_sha256, *(ref.sha256 for ref in refs)]


def _is_sha(value: str) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _is_int(value: object, expected: int) -> bool:
    return type(value) is int and value == expected


def _is_utc(moment: datetime) -> bool:
    return moment.utcoffset() == timedelta(0)  # one spelling per instant: equal records, equal bytes


def _sorted_unique(keys: list) -> bool:
    return keys == sorted(set(keys))


def _candidate_key(candidate: Candidate) -> tuple[str, str]:
    return candidate.version, candidate.decision.path
