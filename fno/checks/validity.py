"""Hard-validity checks (story C4, design 7 and 12.4): every proposed trade is re-checked by code independent of the
code that proposed it. Common checks:
- evidence: the committed snapshot and its hashes, its day and cutoff;
- NSE's listing: a monthly expiry, the lot size;
- every leg listed, and quoted before the cutoff at the price used;
- the maximum loss, recomputed, and fixed at entry (no naked short leg, story STR1);
- every owner limit, recomputed from the ledger, the snapshot and the margins file.

The book's mode adds its own checks. A failure is final: no path, the owner's included, turns it into a pass."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .data_checks import CaptureRecord
from .validity_account import AccountProblem
from .validity_evidence import EvidenceReader
from .validity_limits import LimitChecks
from .validity_listing import NseListing
from .validity_market import listing_checks, snapshot_checks
from .validity_modes import ValidityMode
from .validity_money import max_loss, uncovered_types
from .validity_proposal import CheckResult, ValidityProposal

LOSS_TOLERANCE = 1.0  # rupees (criterion 1: a maximum loss wrong by Rs 1 or more fails)


class HardValidityError(ValueError):
    """A hard-validity failure: it can never be overridden."""


@dataclass(frozen=True)
class ValidityReport:
    book: str
    opportunity_id: str
    mode: str
    results: tuple[CheckResult, ...]

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    @property
    def failures(self) -> tuple[CheckResult, ...]:
        return tuple(r for r in self.results if not r.ok)

    def record(self) -> dict:
        return {"mode": self.mode, "ok": self.ok, "checks": [r.record() for r in self.results]}


def override(report: ValidityReport, by: str, reason: str) -> ValidityReport:
    """Criterion 3: nobody, the owner included, overrides a hard-validity failure; a passing report needs nothing."""
    if not report.ok:
        failed = ", ".join(r.name for r in report.failures)
        raise HardValidityError(f"{by} cannot override hard validity ({failed}): {reason!r} refused")
    return report


@dataclass(frozen=True)
class Sources:
    """Where C4 reads its raw inputs: the snapshot store, NSE's listing and the books' ledgers."""

    snapshots: EvidenceReader
    listing: NseListing
    accounts: object  # `facts(book, cutoff) -> AccountFacts` (raises AccountProblem)


class ValidityChecker:
    def __init__(self, sources: Sources, limits: LimitChecks, modes: Mapping[str, ValidityMode]):
        self.sources, self.limits, self.modes = sources, limits, dict(modes)

    def check(self, proposal: ValidityProposal, capture: CaptureRecord | None) -> ValidityReport:
        mode = self.modes[proposal.book]
        evidence, problems = self.sources.snapshots.read(proposal.day, capture)
        results = [CheckResult("evidence", not problems, "; ".join(problems) or "committed snapshot, hashes equal")]
        if evidence is not None:
            results += snapshot_checks(proposal, evidence)
        results += self._listing(proposal) + self._money(proposal) + self._limits(proposal, evidence)
        verdicts = proposal.risk_verdicts_ok
        results.append(
            CheckResult("risk_verdicts", verdicts, f"C2's own verdicts {'passed' if verdicts else 'failed'}")
        )
        results += mode.checks(proposal, evidence)
        return ValidityReport(proposal.book, proposal.opportunity_id, mode.name, tuple(results))

    def _listing(self, proposal: ValidityProposal) -> list[CheckResult]:
        listing, missing = self.sources.listing.read(proposal.day)
        if listing is None:
            return [CheckResult("listing", False, "; ".join(missing))]
        return [CheckResult("listing", True, "NSE's F&O file read", listing.provenance())] + listing_checks(
            proposal, listing
        )

    def _limits(self, proposal: ValidityProposal, evidence) -> list[CheckResult]:
        try:
            account = self.sources.accounts.facts(proposal.book, proposal.cutoff)
        except AccountProblem as problem:
            return [CheckResult("account", False, str(problem))]
        return self.limits.checks(proposal, account, evidence)

    def _money(self, proposal: ValidityProposal) -> list[CheckResult]:
        legs = [leg.leg for leg in proposal.legs]
        naked = uncovered_types(legs)
        loss = max_loss(legs, proposal.units, self.limits.charges)
        off, limit = abs(loss.total - proposal.claimed_max_loss), self.limits.limits.max_loss_per_trade
        numbers = {**loss.numbers(), "claimed": round(proposal.claimed_max_loss, 2), "difference": round(off, 2)}
        return [
            CheckResult("bounded_loss", not naked, f"naked short {naked}" if naked else "every sold leg is covered"),
            CheckResult("max_loss", off < LOSS_TOLERANCE, f"recomputed {loss.total:.2f}", numbers),
            CheckResult("loss_limit", loss.total <= limit, f"recomputed {loss.total:.2f}, limit {limit:g}"),
        ]
