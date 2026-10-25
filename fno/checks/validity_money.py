"""C4's own arithmetic (story C4, design 7): the money of a proposed trade, recomputed without the proposer's code.

Independence (judge-checked by a test that reads this file's imports): nothing here imports `fno.costs`,
`fno.research_engine` or `fno.risk`. Charges come straight from the `charges` table of `config.yaml`. The payoff is
evaluated at expiry on a grid of index levels one point apart across the strikes, not with the proposer's
width-minus-credit formula. The definition is the frozen protocol's (experiment 1, section 4): the worst terminal loss
between the outer strikes, plus entry charges, every pad (entry and exit) and the exit charges at the worst level's
closing prices (where levels tie, the larger charges), every order charged at a price of at least one tick."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

BUY, SELL = "buy", "sell"
TICK = 0.05  # NSE's smallest option price
PAD = 1.0  # rupees per unit on every leg at entry and exit (protocol section 4)
GRID_STEP = 1.0  # index points between evaluated expiry levels; NIFTY strikes are multiples of 50
LOSS_DECIMALS = 6


@dataclass(frozen=True)
class ProposedLeg:
    strike: float
    kind: str  # "CE" or "PE"
    side: int  # +1 bought, -1 sold when opening
    price: float  # entry price per unit, before the pad

    def value_at_expiry(self, level: float) -> float:
        return max(level - self.strike, 0.0) if self.kind == "CE" else max(self.strike - level, 0.0)


def order_charge(price: float, units: int, side: str, table: Mapping[str, float]) -> float:
    """One executed order's charges from the charge table: brokerage, exchange, SEBI, IPFT, GST on those four, STT on
    a sale, stamp duty on a purchase."""
    turnover = max(price, TICK) * units
    brokerage = table["brokerage_per_order"]
    exchange = turnover * table["exchange_txn_pct"] / 100
    sebi = turnover * table["sebi_per_crore"] / 1e7
    ipft = turnover * table["ipft_per_crore"] / 1e7
    gst = (brokerage + exchange + sebi + ipft) * table["gst_pct"] / 100
    stt = turnover * table["stt_sell_pct"] / 100 if side == SELL else 0.0
    stamp = turnover * table["stamp_duty_buy_pct"] / 100 if side == BUY else 0.0
    return brokerage + exchange + sebi + ipft + gst + stt + stamp


def _fill(price: float, buying: bool) -> float:
    return price + PAD if buying else price - PAD


def entry_charges(legs: Sequence[ProposedLeg], units: int, table: Mapping[str, float]) -> float:
    return sum(
        order_charge(_fill(leg.price, leg.side > 0), units, BUY if leg.side > 0 else SELL, table) for leg in legs
    )


def exit_charges(legs: Sequence[ProposedLeg], level: float, units: int, table: Mapping[str, float]) -> float:
    """Closing every leg at its expiry value at `level`: a bought leg is sold, a sold leg is bought back."""
    total = 0.0
    for leg in legs:
        closing_buy = leg.side < 0
        total += order_charge(
            _fill(leg.value_at_expiry(level), closing_buy), units, BUY if closing_buy else SELL, table
        )
    return total


def expiry_grid(legs: Sequence[ProposedLeg]) -> list[float]:
    low, high = min(leg.strike for leg in legs), max(leg.strike for leg in legs)
    steps = round((high - low) / GRID_STEP)
    return [low + n * GRID_STEP for n in range(steps + 1)]


def uncovered_types(legs: Sequence[ProposedLeg]) -> list[str]:
    """The option types with more legs sold than bought: a naked short call has no loss limit, a naked short put none
    short of the index at 0. With none, the payoff is flat or rising beyond the outer strikes, so the grid above holds
    the worst level (story STR1: the maximum loss must be fixed at entry)."""
    return [kind for kind in ("CE", "PE") if sum(leg.side for leg in legs if leg.kind == kind) < 0]


def loss_per_unit(legs: Sequence[ProposedLeg], level: float) -> float:
    """What the position loses per unit if held to expiry with the index at `level` (entry premium included)."""
    return -sum(leg.side * (leg.value_at_expiry(level) - leg.price) for leg in legs)


@dataclass(frozen=True)
class MaxLoss:
    total: float
    payoff_loss: float  # per unit, at the worst level
    worst_level: float
    entry_charges: float
    exit_charges: float
    pads: float

    def numbers(self) -> dict:
        return {key: round(value, 2) for key, value in vars(self).items()}


def max_loss(legs: Sequence[ProposedLeg], units: int, table: Mapping[str, float]) -> MaxLoss:
    worst = max(
        (round(loss_per_unit(legs, level), LOSS_DECIMALS), exit_charges(legs, level, units, table), level)
        for level in expiry_grid(legs)
    )
    loss, closing, level = worst
    entry, pads = entry_charges(legs, units, table), 2 * len(legs) * PAD * units
    return MaxLoss(loss * units + entry + pads + closing, loss, level, entry, closing, pads)


def entry_cash_flow(legs: Sequence[ProposedLeg], units: int, table: Mapping[str, float]) -> float:
    """Cash the entry moves: premium in for sold legs, out for bought ones, at the padded price, less charges."""
    paid = sum(-leg.side * _fill(leg.price, leg.side > 0) * units for leg in legs)
    return paid - entry_charges(legs, units, table)
