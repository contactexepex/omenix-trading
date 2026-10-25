"""C4's market checks (story C4): the snapshot is the decision day's and started by the cutoff; every leg is
listed in it under the contract name the trade records (E4 fills and marks by name: judge 83 addendum 1), quoted by
the cutoff, at the price the proposal used. Against NSE's own listing (judge 83):
- the expiry is a listed monthly one, every leg on it;
- the lot size is NSE's for that expiry."""

from __future__ import annotations

from .validity_evidence import Evidence
from .validity_listing import Listing
from .validity_proposal import CheckResult, ValidityLeg, ValidityProposal

PRICE_TOLERANCE = 1e-6  # rupees per unit


def snapshot_checks(proposal: ValidityProposal, evidence: Evidence) -> list[CheckResult]:
    started = evidence.started_at
    same_day = started.date() == proposal.day and started <= proposal.cutoff
    day_reason = f"snapshot started {started.isoformat()}; day {proposal.day}, cutoff {proposal.cutoff.isoformat()}"
    return [CheckResult("date", same_day, day_reason)] + [_leg_check(proposal, evidence, leg) for leg in proposal.legs]


def listing_checks(proposal: ValidityProposal, listing: Listing) -> list[CheckResult]:
    monthly = proposal.expiry in listing.monthly_expiries
    same = all(leg.expiry == proposal.expiry for leg in proposal.legs)
    lots = listing.lot_sizes.get(proposal.expiry, frozenset())
    expiry_reason = f"opportunity {proposal.expiry}; NSE's monthly {list(listing.monthly_expiries)}"
    lot_reason = f"proposal {proposal.lot_size} units a lot; NSE {sorted(lots, key=str)} for {proposal.expiry}"
    return [
        CheckResult("expiry", monthly and same, expiry_reason, listing.provenance()),
        CheckResult("lot_size", lots == {proposal.lot_size}, lot_reason, listing.provenance()),
    ]


def _leg_check(proposal: ValidityProposal, evidence: Evidence, leg: ValidityLeg) -> CheckResult:
    name = f"leg {leg.expiry} {leg.leg.strike:g} {leg.leg.kind}"
    row = evidence.rows.get((leg.expiry, leg.leg.strike, leg.leg.kind))
    if row is None:
        return CheckResult(name, False, "not listed in the snapshot")
    if row.contract != leg.contract:
        return CheckResult(name, False, f"named {leg.contract}, but the snapshot lists this leg as {row.contract}")
    if row.received_at is None or row.received_at > proposal.cutoff:
        return CheckResult(name, False, f"quoted at {row.received_at}, not before the cutoff")
    if row.a4_problem:
        return CheckResult(name, False, f"quote not usable by A4's rule: {row.a4_problem}")
    numbers = {"price": leg.leg.price, "snapshot_mid": row.mid}
    if row.mid is None or abs(row.mid - leg.leg.price) > PRICE_TOLERANCE:
        return CheckResult(name, False, "price differs from the snapshot mid", numbers)
    return CheckResult(name, True, "listed, quoted before the cutoff, price equals the snapshot mid", numbers)
