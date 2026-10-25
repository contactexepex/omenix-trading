"""The day's decision (story REC1b, section 1): the facts the inputs gathered, turned into the one recommendation by the
closed reason order, first match wins. It never makes, fills or prices a trade: a `PAPER_TRADE` names a trade an
established version already made and sealed. With several such trades the first in candidate order is named; the
others stay listed as candidates (none can exist before a version reaches rung 3)."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, datetime

from .constants import (
    BLOCKS_REAL_MONEY,
    RECORD_KIND,
    RECORD_SCHEMA_VERSION,
    EvidenceRung,
    NoTradeReason,
    PaperAnswer,
    RealMoneyAnswer,
    SourceState,
)
from .contracts import Candidate, CandidateSource, Recommendation, source_of
from .refs import RecordRef
from .rungs import RUNG_RULE_SHA256, VersionEvidence


@dataclass(frozen=True)
class DayFacts:
    """Everything the decision reads, gathered and checked by the inputs; `data_ok` is False when any input failed."""

    session: date
    made_at: datetime
    code_commit: str
    config_sha256: str
    inputs: tuple[RecordRef, ...]
    versions: tuple[VersionEvidence, ...]
    candidates: tuple[Candidate, ...]
    sources: tuple[CandidateSource, ...]
    data_ok: bool
    step_problems: bool
    quote_gate_failed: bool
    weather_red: bool
    risk_refused: Collection[str] = ()  # established versions whose trade C2/C4 or a safety law refused today
    braked: Collection[str] = ()  # established versions held by a brake or the daily stop
    rm1_eligible: Collection[str] = ()  # versions RM1's report names eligible on this day


def decide(facts: DayFacts) -> Recommendation:
    established = [v.version for v in facts.versions if v.rung is EvidenceRung.ESTABLISHED]
    reason = _reason(facts, established)
    trade = None if reason else _first_trade(facts)
    if trade is None and reason is None:
        reason = _without_trade(facts, established)
    eligible = None if reason in BLOCKS_REAL_MONEY else _eligible(facts, established)
    real_money = RealMoneyAnswer.ELIGIBLE_FOR_YOUR_OWN_REVIEW if eligible else RealMoneyAnswer.DO_NOT_TRADE_REAL_MONEY
    braked = tuple(sorted(set(facts.braked) & set(established)))  # only an established version's brake can matter
    return Recommendation(
        schema_version=RECORD_SCHEMA_VERSION, kind=RECORD_KIND, session=facts.session, made_at=facts.made_at,
        evidence_cutoff=facts.made_at, code_commit=facts.code_commit, config_sha256=facts.config_sha256,
        rung_rule_sha256=RUNG_RULE_SHA256, inputs=facts.inputs, versions=facts.versions, candidates=facts.candidates,
        candidate_sources=facts.sources, braked_versions=braked, real_money=real_money, eligible_version=eligible,
        paper=PaperAnswer.NO_TRADE if reason else PaperAnswer.PAPER_TRADE, paper_trade=trade, reason=reason,
    )  # fmt: skip


def _reason(facts: DayFacts, established: list[str]) -> NoTradeReason | None:
    """The reasons that hold whatever was traded, in the closed order."""
    unread = {s.name for s in facts.sources if s.state is SourceState.UNAVAILABLE}
    if not facts.data_ok or any(source_of(v) in unread for v in established) or disagreeing(facts, established):
        return NoTradeReason.DATA_CHECK_FAILED
    if facts.step_problems:
        return NoTradeReason.STEP_PROBLEMS
    if not established:
        return NoTradeReason.NO_ESTABLISHED_VERSION
    if facts.quote_gate_failed:
        return NoTradeReason.QUOTE_GATE_FAILED
    return NoTradeReason.WEATHER_RED if facts.weather_red else None


def disagreeing(facts: DayFacts, established: list[str]) -> list[str]:
    """Versions RM1 names eligible below rung 3: the two gates contradict, so nothing is trusted (judge 654 S1)."""
    return sorted(set(facts.rm1_eligible) - set(established))


def _first_trade(facts: DayFacts) -> Candidate | None:
    return next((c for c in facts.candidates if c.traded and c.rung is EvidenceRung.ESTABLISHED), None)


def _without_trade(facts: DayFacts, established: list[str]) -> NoTradeReason:
    if any(v in facts.risk_refused for v in established):
        return NoTradeReason.RISK_CAP
    return NoTradeReason.BRAKE if any(v in facts.braked for v in established) else NoTradeReason.NO_CANDIDATE


def _eligible(facts: DayFacts, established: list[str]) -> str | None:
    """A version under its own brake or daily stop is never eligible (orchestrator's ruling, judge 654.1)."""
    return next((v for v in established if v in facts.rm1_eligible and v not in facts.braked), None)
