"""What C4 checks (story C4): one proposed trade as plain values, and the result of one check with its numbers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING

from .validity_money import ProposedLeg

if TYPE_CHECKING:
    from ..playbook.envelope import BookTerms


@dataclass(frozen=True)
class ValidityLeg:
    contract: str
    expiry: str  # ISO date
    leg: ProposedLeg  # strike, type, side and the entry price the proposal used


@dataclass(frozen=True)
class ValidityProposal:
    book: str
    opportunity_id: str
    day: date
    cutoff: datetime  # the decision cutoff, time zone aware
    expiry: str  # the opportunity's expiry, ISO
    structure: str  # SF, SC, BF or a STR1 code (LC, LP, CDS, CCS, PDS, PCS)
    width: float
    lots: int
    lot_size: int
    legs: tuple[ValidityLeg, ...]
    claimed_max_loss: float
    risk_verdicts_ok: bool  # every C2 verdict recorded for the trade passed
    rule_sha256: str  # the version fingerprint the decision used
    strategy: object | None = None  # the playbook version (playbook mode)
    approved: frozenset[tuple[str, int]] = field(default_factory=frozenset)  # versions tradable on the day
    earlier: tuple[ValidityProposal, ...] = ()  # the book's trades chosen earlier the same day that passed C4
    open_terms: Mapping[str, tuple[str, float, int]] = field(default_factory=dict)  # open trade -> recorded terms
    premium_reserved: float = 0.0  # premium held for pending orders (E4)
    # Book 2 (story D4): the rule's own terms, None when the rules offer no trade. Taken from D2's evaluation, never
    # from the decider: a decider's default equal to its own choice would read as follow_rule (judge 260)
    rule_default: BookTerms | None = None
    eligible: frozenset[tuple[str, int]] = frozenset()  # Book 2: D2's versions that fired with a valid candidate
    strategy_id: str = ""  # Book 3 (story D5): the registered strategy the trade uses

    @property
    def units(self) -> int:
        return self.lots * self.lot_size

    @property
    def terms(self) -> tuple[str, float, int]:
        return self.structure, self.width, self.lots


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    reason: str
    numbers: Mapping[str, object] = field(default_factory=dict)

    def record(self) -> dict:
        return {"check": self.name, "ok": self.ok, "reason": self.reason, "numbers": dict(self.numbers)}
