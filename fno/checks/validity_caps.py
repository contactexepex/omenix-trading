"""Story C5's caps as C4 recomputes them (judge 83: every C2 limit, with C4's own arithmetic): the paper account size,
and the bucket, open-risk and new-risk-per-day caps on sums of maximum losses. A position with two sides counts its
full maximum loss in each of its buckets (owner, 15 Oct 2026, "1 B"); new risk counts every trade first filled this
session, open or closed, at the largest maximum loss it carried (owner, "3 A").

Nothing here comes from C2 (`fno.risk`). A position's bucket is its contracts' underlying (`fno/contract_symbols.py`,
the symbol format's rule for Groww's and NSE's IDs alike: NIFTY or BANKNIFTY) and its structure's side from
`bucket_sides` in config.yaml. A held position's maximum loss is C4's own: its cash so far plus its worst value at
expiry on C4's one-point grid between its outer strikes, plus each leg's exit pad and exit charges at that level (where
levels tie, the larger charges), never below zero; a tail with more options sold than bought is not defined risk and
fails. The proposal's is `validity_money`'s. Contract strikes come from the committed snapshot, so an open contract
missing from it fails the check."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..constants import BUCKET_INDEX_GROUPS
from ..contract_symbols import underlying_of
from .validity_account import AccountFacts, Position
from .validity_chain import PricedChain
from .validity_money import BUY, PAD, SELL, ProposedLeg, expiry_grid, order_charge
from .validity_pricing import PricingProblem
from .validity_proposal import CheckResult
from .validity_settings import CapLimits

LOSS_DECIMALS = 6


class CapProblem(ValueError):
    """A position C4 cannot place in a bucket or measure: the cap check fails closed."""


@dataclass(frozen=True)
class Exposure:
    trade_id: str
    buckets: tuple[tuple[str, str], ...]  # (underlying group, side), one per side of the structure
    max_loss: float


def buckets_of(structure: str | None, contracts, sides: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    """A structure's sides from config.yaml: one name, or a list (a directional spread, owner 15 Oct 2026 "1 B")."""
    groups = {underlying_of(c) for c in contracts}
    if len(groups) != 1 or next(iter(groups)) not in BUCKET_INDEX_GROUPS or structure not in sides:
        raise CapProblem(f"unmapped bucket: structure {structure!r} on underlyings {sorted(groups)}")
    listed = sides[structure]
    return tuple((next(iter(groups)), side) for side in ([listed] if isinstance(listed, str) else listed))


def held_max_loss(position: Position, chain: PricedChain, table: Mapping[str, float]) -> float:
    legs = []
    for contract, units in position.units.items():
        if contract not in chain.quotes:
            raise PricingProblem(f"{contract} is not in the snapshot: its strike is unknown")
        _, strike, kind = chain.quotes[contract][0]
        legs.append((ProposedLeg(strike, kind, 1 if units > 0 else -1, 0.0), abs(units)))
    if not legs:
        return 0.0
    for kind in ("CE", "PE"):
        if sum(leg.side * n for leg, n in legs if leg.kind == kind) < 0:
            raise CapProblem(f"{position.trade_id}: more {kind} sold than bought, its loss is not capped")

    def exit_charges(level: float) -> float:
        return sum(
            order_charge(leg.value_at_expiry(level) + (PAD if leg.side < 0 else -PAD), n, BUY if leg.side < 0 else SELL,
                         table)
            for leg, n in legs
        )  # fmt: skip

    worst = max(
        (round(-sum(leg.side * n * leg.value_at_expiry(level) for leg, n in legs), LOSS_DECIMALS), exit_charges(level))
        for level in expiry_grid([leg for leg, _ in legs])
    )
    return max(worst[0] - position.cash_flow + PAD * sum(n for _, n in legs) + worst[1], 0.0)


def _cap(name: str, groups: Sequence[tuple[str, dict[str, float]]], limit: float) -> CheckResult:
    totals = [(what, counted, sum(counted.values())) for what, counted in groups]
    numbers = {what: {"total_rs": round(total, 2), "counted_rs": {k: round(v, 2) for k, v in counted.items()}}
               for what, counted, total in totals} | {"limit_rs": limit}  # fmt: skip
    reason = "; ".join(f"{what}: maximum losses Rs {total:,.2f} against the cap Rs {limit:,.0f}"
                       for what, _, total in totals)  # fmt: skip
    return CheckResult(name, all(total <= limit for _, _, total in totals), reason, numbers)


class CapChecks:
    def __init__(self, caps: CapLimits, rules: Sequence[str], table: Mapping[str, float]):
        self.caps, self.rules, self.table = caps, tuple(rules), dict(table)

    def exposure(self, position: Position, chain: PricedChain) -> Exposure:
        structure = position.terms[0] if position.terms else None
        buckets = buckets_of(structure, position.units, self.caps.sides)
        return Exposure(position.trade_id, buckets, held_max_loss(position, chain, self.table))

    def session_risk(self, trade_id: str, states, chain: PricedChain) -> float:
        """The largest maximum loss a session trade carried after any fill time (owner, "3 A": closed ones count)."""
        return max((held_max_loss(Position(trade_id, u, c), chain, self.table) for u, c in states), default=0.0)

    def checks(self, held: Sequence[Position], session, own: Exposure, chain: PricedChain) -> list[CheckResult]:
        """`held`: open trades and those chosen earlier the same day; `session`: trades first filled today, with
        their states; `own`: the proposal's buckets and maximum loss. Each cap fails closed on its own inputs."""
        mine = {own.trade_id: own.max_loss}

        def others() -> list[Exposure]:
            return [self.exposure(p, chain) for p in held]

        def bucket() -> CheckResult:
            exposures = others()
            groups = [(f"bucket {'/'.join(b)}", {e.trade_id: e.max_loss for e in exposures if b in e.buckets} | mine)
                      for b in own.buckets]  # fmt: skip
            return _cap("bucket_cap", groups, self.caps.bucket)

        def open_risk() -> CheckResult:
            everything = {e.trade_id: e.max_loss for e in others()} | mine
            return _cap("open_risk_cap", [("all open positions", everything)], self.caps.open_risk)

        def new_risk() -> CheckResult:
            today = {trade: self.session_risk(trade, states, chain) for trade, states in session} | mine
            return _cap("new_risk_per_day", [("trades opened this session", today)], self.caps.new_risk_per_day)

        caps = {"bucket_cap": bucket, "open_risk_cap": open_risk, "new_risk_per_day": new_risk}
        return [_failing_closed(name, caps[name]) for name in caps if name in self.rules]


def _failing_closed(name: str, check) -> CheckResult:
    try:
        return check()
    except (CapProblem, PricingProblem) as problem:
        return CheckResult(name, False, str(problem))


def paper_account_check(account: AccountFacts, paper_account: float) -> CheckResult:
    capital = account.closed_equity[0][1]  # the opening plus top-ups written by the cutoff (story E1b)
    reason = f"the account's capital is Rs {capital:,.2f}; the profile's paper account is Rs {paper_account:,.2f}"
    return CheckResult("paper_account", capital == paper_account, reason, {"capital_rs": capital})
