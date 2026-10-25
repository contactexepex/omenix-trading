"""Gathering the day's facts (story REC1b): every port is read once; a port that fails makes the day
`data_check_failed` and is named in `problems`, and its part of the facts is left empty, never guessed. Each version's
rung comes from its own outcomes and reports (judge 641 m1), never from whether a candidate source could be read."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from .constants import CandidateSourceName, EvidenceRung, SourceState
from .contracts import Candidate, CandidateSource
from .decide import DayFacts
from .ports import CandidateSourcePort, ConditionsPort, EligibilityPort, EvidencePort, InputFailed, SourceReading
from .rungs import VersionEvidence, evidence

FAILED = "{what} could not be read: {why}"
UNREAD_STATUS = "input_failed"  # a source whose own reading failed: unavailable, with this as its status
DISAGREE = "RM1 names {version} eligible, but its rung is {rung}: the two gates disagree (judge 654 S1)"


@dataclass(frozen=True)
class Header:
    """What identifies the run that decides: its code and its settings."""

    code_commit: str
    config_sha256: str


@dataclass(frozen=True)
class Gathered:
    facts: DayFacts
    problems: tuple[str, ...]  # one line per failed input, for the alert; empty on a clean day


@dataclass(frozen=True)
class Ports:
    sources: tuple[CandidateSourcePort, ...]
    evidence: EvidencePort
    conditions: ConditionsPort
    eligibility: EligibilityPort


def gather(day: date, made_at: datetime, header: Header, ports: Ports) -> Gathered:
    problems: list[str] = []
    versions = _attempt(problems, "the versions' evidence", lambda: _evidence(day, made_at, ports.evidence), ())
    rungs = {v.version: v.rung for v in versions}
    readings = [_reading(problems, port, day) for port in ports.sources]
    conditions = _attempt(problems, "the day's conditions", lambda: ports.conditions.conditions(day), None)
    eligible = _attempt(problems, "RM1's eligibility", lambda: ports.eligibility.eligible(day), frozenset())
    candidates = [Candidate(d.version, rungs[d.version], d.decision, d.traded) for r in readings for d in r.decisions
                  if _rated(problems, rungs, d.version)]  # fmt: skip
    used = {ref for r in readings for ref in r.used} | set(conditions.used if conditions else ())
    problems += [DISAGREE.format(version=v, rung=rungs.get(v, "not rated")) for v in sorted(eligible)
                 if rungs.get(v) is not EvidenceRung.ESTABLISHED]  # fmt: skip
    facts = DayFacts(
        session=day, made_at=made_at, code_commit=header.code_commit, config_sha256=header.config_sha256,
        inputs=tuple(sorted(used, key=lambda ref: ref.path)), versions=tuple(sorted(versions, key=_version)),
        candidates=tuple(sorted(candidates, key=lambda c: (c.version, c.decision.path))),
        sources=tuple(sorted((r.source for r in readings), key=lambda s: s.name)), data_ok=not problems,
        step_problems=bool(conditions and conditions.step_problems),
        quote_gate_failed=bool(conditions and conditions.quote_gate_failed),
        weather_red=bool(conditions and conditions.weather_red), rm1_eligible=eligible,
    )  # fmt: skip
    return Gathered(facts, tuple(problems))


def _evidence(day: date, made_at: datetime, port: EvidencePort) -> tuple[VersionEvidence, ...]:
    outcomes = port.outcomes(day, made_at)
    return tuple(evidence(outcomes, v, day, made_at, port.reports(v)) for v in port.versions(day))


def _reading(problems: list[str], port: CandidateSourcePort, day: date) -> SourceReading:
    try:
        return port.read(day)
    except InputFailed as failed:
        problems.append(FAILED.format(what=f"candidate source {port.name}", why=failed))
        return _unread(port.name)


def _unread(name: CandidateSourceName) -> SourceReading:
    return SourceReading(CandidateSource(name, SourceState.UNAVAILABLE, UNREAD_STATUS), (), ())


def _rated(problems: list[str], rungs: dict, version: str) -> bool:
    """A decision of a version the evidence does not rate cannot get a rung: an input gap, never a guess."""
    if version in rungs:
        return True
    problems.append(FAILED.format(what=f"the evidence of {version}", why="the version is not rated"))
    return False


def _attempt(problems: list[str], what: str, read: Callable, empty):
    try:
        return read()
    except InputFailed as failed:
        problems.append(FAILED.format(what=what, why=failed))
        return empty


def _version(evidence_line: VersionEvidence) -> str:
    return evidence_line.version
