"""Stress and exposure as C4 recomputes them (story C4, judge 83), on its own pricing (`validity_pricing`). Every leg
of the book's open trades, the trades chosen earlier the same day and the proposal is revalued under each shock.
- Stress: the open trades' loss from their marks plus the proposal's loss from its entry (its pads and charges
  count), in the worst configured scenario, at most the owner's limit.
- Exposure (design 8.1): every position's loss from its marks for a NIFTY move either way and for a volatility rise,
  no time passing, each at most its limit."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from .validity_account import Position
from .validity_chain import PricedChain
from .validity_proposal import CheckResult
from .validity_settings import Shock, ValidityLimits


def marked(position: Position, chain: PricedChain) -> float:
    return sum(n * chain.mid(contract) for contract, n in position.units.items())


def shocked(position: Position, chain: PricedChain, shock: Shock, day: date, rate: float) -> float:
    return sum(
        n * chain.leg(contract).value(day, rate, shock.move_pct, shock.sigma_factor, shock.sigma_add, shock.days)
        for contract, n in position.units.items()
    )


class StressChecks:
    def __init__(self, chain: PricedChain, limits: ValidityLimits, day: date):
        self.chain, self.limits, self.day = chain, limits, day

    def _loss_from_marks(self, position: Position, shock: Shock) -> float:
        return marked(position, self.chain) - shocked(position, self.chain, shock, self.day, self.limits.rate)

    def stress(self, held: Sequence[Position], proposal: Position) -> CheckResult:
        counted = {}
        for shock in self.limits.scenarios:
            from_entry = -(proposal.cash_flow + shocked(proposal, self.chain, shock, self.day, self.limits.rate))
            counted[shock.name] = sum(self._loss_from_marks(p, shock) for p in held) + from_entry
        worst = max(counted, key=counted.get)
        limit = self.limits.max_stress_loss
        numbers = {"worst": worst, "worst_loss_rs": round(counted[worst], 2), "limit_rs": limit,
                   "scenarios": {name: round(loss, 2) for name, loss in counted.items()}}  # fmt: skip
        reason = f"worst scenario {worst}: Rs {counted[worst]:,.2f} against the limit Rs {limit:,.0f}"
        return CheckResult("stress_loss", counted[worst] <= limit, reason, numbers)

    def exposure(self, positions: Sequence[Position]) -> CheckResult:
        move = max(sum(self._loss_from_marks(p, s) for p in positions) for s in self.limits.exposure_moves)
        iv = sum(self._loss_from_marks(p, self.limits.exposure_iv) for p in positions)
        limits = self.limits
        ok = move <= limits.max_move_loss and iv <= limits.max_iv_loss
        numbers = {"move_loss_rs": round(move, 2), "iv_rise_loss_rs": round(iv, 2),
                   "max_move_loss_rs": limits.max_move_loss, "max_iv_loss_rs": limits.max_iv_loss}  # fmt: skip
        reason = f"move loss Rs {move:,.2f} (limit {limits.max_move_loss:,.0f}), IV-rise loss Rs {iv:,.2f} " \
                 f"(limit {limits.max_iv_loss:,.0f})"  # fmt: skip
        return CheckResult("exposure_limit", ok, reason, numbers)
