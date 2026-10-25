"""The playbook file format (story D1, design section 5): one strategy version, every field required.

A file is a YAML mapping with exactly the fields below; `evidence` values stay empty (null) until the strategy is
approved. The version's fingerprint (`parameters_sha256`) covers every field except `status` and `evidence`: those two
change through the registry's lifecycle, everything else is the tested rule, and changing it makes a new version."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date

from ..constants import NO_ESTIMATE, NUMBER_OPERATORS, OPERATOR_IS, PlaybookStatus
from ..research_engine.live_validation import MIN_AGREEMENT, MIN_AVAILABLE, MIN_DAYS, LiveUseRule
from .fields import Fields, PlaybookError
from .structure_spec import STRUCTURE, StructureSpec, parse_structure
from .vocabulary import FEATURES, FLAG

TOP = (
    "name", "version", "status", "payer", "edge_family", "structure", "entry_conditions", "live_use_rule",
    "size_rule", "funding", "exits", "evaluation_plan", "evidence",
)  # fmt: skip
CONDITION = ("feature", "operator", "threshold")
USE_RULE = ("min_days", "min_agreement", "min_available")
FUNDING = ("margin_per_lot", "source", "date")
EXITS = ("time", "profit", "loss", "event")
PLAN = (
    "expected_range", "expected_net_per_opportunity", "expected_net_source", "unit", "review_dates", "pause_rules",
    "catastrophic_loss_rs",
)  # fmt: skip
RANGE = ("low", "high")
EVIDENCE = (
    "test_results_path", "test_results_commit", "red_team_note", "judge_verdict", "freeze_record",
    "owner_approval_date",
)  # fmt: skip
LIFECYCLE_FIELDS = ("status", "evidence")  # outside the fingerprint
NAME_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{7,40}")


@dataclass(frozen=True)
class EntryCondition:
    feature: str  # the research feature it was tested on (vocabulary.FEATURES)
    operator: str
    threshold: float | bool


@dataclass(frozen=True)
class Evidence:
    """Where the approval comes from, whatever the test was (a historical experiment or a forward test): the results
    and their commit, the red-team note, the judge's verdict, the frozen protocol's freeze record, and the date the
    owner approved it. Paths are relative to the repository."""

    test_results_path: str | None
    test_results_commit: str | None
    red_team_note: str | None
    judge_verdict: str | None
    freeze_record: str | None
    owner_approval_date: date | None

    @property
    def missing(self) -> list[str]:
        return [field for field in EVIDENCE if getattr(self, field) is None]

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(
            p for p in (self.test_results_path, self.red_team_note, self.judge_verdict, self.freeze_record) if p
        )


@dataclass(frozen=True)
class Strategy:
    name: str
    version: int
    status: PlaybookStatus
    payer: str
    edge_family: str
    structure: StructureSpec
    entry_conditions: tuple[EntryCondition, ...]
    live_use_rule: LiveUseRule
    size_rule: str
    funding: dict
    exits: dict
    evaluation_plan: dict
    evidence: Evidence
    parameters_sha256: str

    @property
    def key(self) -> tuple[str, int]:
        return self.name, self.version

    @property
    def file_name(self) -> str:
        return file_name(self.name, self.version)

    @property
    def live_features(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(FEATURES[c.feature].live_version for c in self.entry_conditions))


def file_name(name: str, version: int) -> str:
    return f"{name}-v{version}.yaml"


def parameters_sha256(document: dict) -> str:
    """SHA-256 of the parsed rule (not the file's bytes: a comment or spacing edit is not a parameter change)."""
    rule = {key: value for key, value in document.items() if key not in LIFECYCLE_FIELDS}
    canonical = json.dumps(rule, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_strategy(document: object) -> Strategy:
    """The strategy in a parsed document; PlaybookError naming the field otherwise."""
    top = Fields(document, "", TOP)
    name = top.text("name")
    if not NAME_PATTERN.fullmatch(name):
        raise top.refuse("name", "must be lower-case letters and digits joined by single hyphens")
    return Strategy(
        name=name,
        version=top.whole("version", 1),
        status=PlaybookStatus(top.choice("status", list(PlaybookStatus))),
        payer=top.text("payer"),
        edge_family=top.text("edge_family"),
        structure=parse_structure(top.section("structure", STRUCTURE)),
        entry_conditions=tuple(_condition(c) for c in top.items("entry_conditions", CONDITION)),
        live_use_rule=_use_rule(top.section("live_use_rule", USE_RULE)),
        size_rule=top.text("size_rule"),
        funding=_funding(top.section("funding", FUNDING)),
        exits=_texts(top.section("exits", EXITS), EXITS),
        evaluation_plan=_plan(top.section("evaluation_plan", PLAN)),
        evidence=_evidence(top.section("evidence", EVIDENCE)),
        parameters_sha256=parameters_sha256(document),
    )


def _condition(fields: Fields) -> EntryCondition:
    feature = fields.choice("feature", FEATURES)
    if FEATURES[feature].kind == FLAG:
        fields.choice("operator", (OPERATOR_IS,))
        threshold = fields.raw("threshold")
        if not isinstance(threshold, bool):
            raise fields.refuse("threshold", "a flag feature compares with true or false")
        return EntryCondition(feature, OPERATOR_IS, threshold)
    return EntryCondition(feature, fields.choice("operator", NUMBER_OPERATORS), fields.number("threshold"))


def _use_rule(fields: Fields) -> LiveUseRule:
    """Frozen per strategy (B7); the owner may set it stricter than B7's proposal, never looser."""
    rule = LiveUseRule(
        fields.whole("min_days", MIN_DAYS), fields.number("min_agreement"), fields.number("min_available")
    )
    for key, floor in (("min_agreement", MIN_AGREEMENT), ("min_available", MIN_AVAILABLE)):
        if not floor <= getattr(rule, key) <= 1:
            raise fields.refuse(key, f"must be between {floor} and 1")
    return rule


def _funding(fields: Fields) -> dict:
    return {
        "margin_per_lot": fields.number("margin_per_lot", positive=True), "source": fields.text("source"),
        "date": fields.day("date"),
    }  # fmt: skip


def _texts(fields: Fields, keys: tuple[str, ...]) -> dict:
    return {key: fields.text(key) for key in keys}


def _plan(fields: Fields) -> dict:
    span = fields.section("expected_range", RANGE)
    low, high = span.number("low"), span.number("high")
    if low > high:
        raise span.refuse("low", "must not be above high")
    return {
        "expected_range": (low, high), "expected_net_per_opportunity": _expected_net(fields),
        "expected_net_source": fields.text("expected_net_source"),
        "unit": fields.text("unit"), "review_dates": fields.days("review_dates"),
        "pause_rules": fields.texts("pause_rules"),
        # the machine-checked pause rule (story E6): one closed trade's net loss (C1) at or beyond this pauses the
        # version at once in every book; the owner's per-trade cap is Rs 10,000
        "catastrophic_loss_rs": fields.number("catastrophic_loss_rs", positive=True),
    }  # fmt: skip


def _expected_net(fields: Fields) -> float | None:
    """The frozen estimate D2 ranks by, or None when a research version has no honest one (`none`); a new estimate is a
    new version, never an update from shadow results."""
    return (
        None
        if fields.raw("expected_net_per_opportunity") == NO_ESTIMATE
        else fields.number("expected_net_per_opportunity")
    )


def _evidence(fields: Fields) -> Evidence:
    commit = fields.optional_text("test_results_commit")
    if commit is not None and not COMMIT_PATTERN.fullmatch(commit):
        raise fields.refuse("test_results_commit", "must be a git commit id (7 to 40 lower-case hex characters)")
    paths = {
        key: fields.optional_text(key)
        for key in ("test_results_path", "red_team_note", "judge_verdict", "freeze_record")
    }
    return Evidence(test_results_commit=commit, owner_approval_date=fields.optional_day("owner_approval_date"), **paths)


def require_evidence(strategy: Strategy, status: PlaybookStatus) -> None:
    """Criterion 4: no `paper` (nor `paused`, which only follows paper) without every evidence field filled."""
    missing = strategy.evidence.missing
    if missing:
        raise PlaybookError(f"evidence.{missing[0]}", f"must be filled for status {status} (missing: {missing})")
