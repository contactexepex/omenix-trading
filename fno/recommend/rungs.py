"""The rung rule (story REC1a, `research/recommend/RUNG_RULE.md`): a version's evidence rung on day d from its
forward outcomes, point in time (judge 620 S2 and m2): a session counts only when it is before d, counted, from
forward paper trading, and GitHub's push receipt of its receipt reached `main` strictly before the decision. An
unknown receipt does not count (fails closed), so a doubt only lowers a rung."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from .constants import EvidenceRung, OutcomeSource
from .refs import RecordRef

RUNG_RULE_PATH = "research/recommend/RUNG_RULE.md"
# The card's SHA-256, pinned to its bytes by tests/recommend/test_rung_rule_card.py; a record carries it
RUNG_RULE_SHA256 = "ba2f079a2a7d3eb0e8452b125227a7ad2b59855fad2bf950a692a5540c70b7e5"
WATCHING_SESSIONS = 30
CALIBRATION_MIN_OUTCOMES = 100
CALIBRATION_MIN_SESSIONS = 60
CALIBRATION_BINS = 5
DAY_CONDITION_STEP = 1


@dataclass(frozen=True)
class ForwardOutcome:
    """One closed outcome of a version, as its sealed record and the counting rule give it."""

    version: str
    session: date
    source: OutcomeSource
    counted: bool  # the counting rule's verdict (MS-P1h `CountingRule`, or S1's order rule for the books)
    receipt_at: datetime | None  # GitHub's push receipt of its receipt commit; None: GitHub could not answer

    def __post_init__(self):
        if self.receipt_at is not None and self.receipt_at.utcoffset() is None:
            raise ValueError("a receipt time without a time zone cannot be compared with the decision")


@dataclass(frozen=True)
class EvidenceReports:
    """The frozen reports a rung above 1 rests on, by path and SHA-256 (judge 629 S1). A report is named only when it
    passed: the P2 review for rung 2; the sample plan, the lower bound and the second window as well for rung 3."""

    review: RecordRef | None = None
    sample_plan: RecordRef | None = None
    lower_bound: RecordRef | None = None
    second_window: RecordRef | None = None

    def refs(self) -> list[RecordRef]:
        return [r for r in (self.review, self.sample_plan, self.lower_bound, self.second_window) if r is not None]

    def established(self) -> bool:
        return None not in (self.sample_plan, self.lower_bound, self.second_window)


@dataclass(frozen=True)
class VersionEvidence:
    """What a record shows per version, so a reader can recount it. Its rung is exactly what the rule gives from its
    own count and reports: a label can never claim more than the evidence it carries (judge 629 S1)."""

    version: str
    rung: EvidenceRung
    counted_sessions: int
    first_session: date | None
    last_session: date | None
    reports: EvidenceReports

    def __post_init__(self):
        if type(self.counted_sessions) is not int or not isinstance(self.rung, EvidenceRung):
            raise ValueError("a version's evidence needs a whole session count and a rung")
        if not _span_fits(self.counted_sessions, self.first_session, self.last_session):
            raise ValueError("a version's first and last sessions do not fit its count")
        if self.rung is not rung_for(self.counted_sessions, self.reports):
            raise ValueError("a version's rung is not what its own count and reports give")


def counted_sessions(outcomes: Iterable[ForwardOutcome], version: str, day: date, made_at: datetime) -> list[date]:
    """The version's distinct sessions that count for a decision on `day` at `made_at`, oldest first."""
    return sorted({o.session for o in outcomes if o.version == version and _counts(o, day, made_at)})


def evidence(outcomes: Iterable[ForwardOutcome], version: str, day: date, made_at: datetime,
             reports: EvidenceReports) -> VersionEvidence:  # fmt: skip
    sessions = counted_sessions(outcomes, version, day, made_at)
    first, last = (sessions[0], sessions[-1]) if sessions else (None, None)
    return VersionEvidence(version, rung_for(len(sessions), reports), len(sessions), first, last, reports)


def rung_for(sessions: int, reports: EvidenceReports) -> EvidenceRung:
    if sessions == 0:
        return EvidenceRung.UNPROVEN
    if sessions < WATCHING_SESSIONS or reports.review is None:
        return EvidenceRung.EXPLORATORY
    return EvidenceRung.ESTABLISHED if reports.established() else EvidenceRung.WATCHING


def lowered(rung: EvidenceRung, conditions: int) -> EvidenceRung:
    """The day's shown rung: one step down per true day condition, never below 0, never up."""
    return EvidenceRung(max(EvidenceRung.UNPROVEN, rung - DAY_CONDITION_STEP * max(conditions, 0)))


def calibration_shown(outcomes: int, sessions: int) -> bool:
    return outcomes >= CALIBRATION_MIN_OUTCOMES and sessions >= CALIBRATION_MIN_SESSIONS


def _counts(outcome: ForwardOutcome, day: date, made_at: datetime) -> bool:
    return (outcome.source is OutcomeSource.FORWARD and outcome.counted and outcome.session < day
            and outcome.receipt_at is not None and outcome.receipt_at < made_at)  # fmt: skip


def _span_fits(count: int, first: date | None, last: date | None) -> bool:
    if count == 0:
        return first is None and last is None
    return first is not None and last is not None and count <= (last - first).days + 1
