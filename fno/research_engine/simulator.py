"""One structure through one monthly cycle, exactly as experiment 1's protocol says (story B2, sections 3-4).

Entry (the cycle's entry day, at the close): the strikes come from the entry day's spot close and option chain.
Widths are tried largest first; a width is skipped when a contract is not listed (`missing_strikes`), a leg has no
usable price or more than half are on settlement (`unfillable`; exactly half is fillable), the prices are impossible
(`bad_prices`: the position is valued at or beyond its worst or best payoff at expiry, so it cannot lose or cannot
win: a short credit at least the width or at most zero, a long debit at most zero or at least the width; owner
decision of 13 Oct 2026) or the modelled maximum loss is above the cap (`no_trade_cap`). The first width that passes is
traded. If none passes, the status is the outcome of the narrowest listed width, or `missing_strikes` when no width
was listed. Exit (the exit day's close) uses the same legs; a leg without a usable price there, or more than half on
settlement, makes the traded width `unfillable`. An exit valued beyond the position's payoff bounds is a traded result,
flagged (`exit_outside_payoff`, report only) so results can show how much rests on impossible closes. Entry never looks
at exit-day data.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..constants import CycleStatus
from ..research_data.panel_reader import NiftyPanel
from .cycle_costs import CycleTerms, PositionCosts
from .cycles import Cycle
from .leg_prices import LegPrice, contracts_on, fill_problem, leg_price
from .structures import Leg, Structure, payoff_bounds, position_value


@dataclass(frozen=True)
class WidthTrial:
    width: float
    outcome: CycleStatus  # TRADED for the width used; otherwise why the width was skipped
    max_loss: float | None = None  # rupees, when the width's entry prices were usable


@dataclass(frozen=True)
class LegResult:
    leg: Leg
    entry: LegPrice
    exit: LegPrice | None = None  # None until the exit is priced


@dataclass(frozen=True)
class CycleResult:
    cycle: Cycle
    structure: str  # the structure's code (SF, SC, BF)
    status: CycleStatus
    widths_tried: tuple[WidthTrial, ...] = ()
    width: float | None = None  # the width traded (or chosen at entry and unfillable at exit)
    legs: tuple[LegResult, ...] = ()
    gross: float = 0.0  # rupees at the raw prices; the money fields are zero unless traded
    charges: float = 0.0
    pads: float = 0.0
    net: float = 0.0  # gross - charges - pads
    max_loss: float | None = None  # modelled maximum loss of the chosen width, rupees
    exit_outside_payoff: bool = False  # report only: a traded exit valued beyond what the position can pay at expiry

    @property
    def needs_settlement(self) -> bool:
        """A traded result that used any settlement price (the no-settlement sensitivity treats it as no trade)."""
        prices = [p for leg in self.legs for p in (leg.entry, leg.exit) if p is not None]
        return self.status == CycleStatus.TRADED and any(p.on_settlement for p in prices)

    @property
    def no_settlement_net(self) -> float:
        return 0.0 if self.needs_settlement else self.net


class CycleSimulator:
    def __init__(self, panel: NiftyPanel, terms: CycleTerms):
        self.panel, self.terms, self.costs = panel, terms, PositionCosts(terms)

    def simulate(self, cycle: Cycle, structure: Structure) -> CycleResult:
        if not cycle.has_entry_window:
            return CycleResult(cycle, structure.code, CycleStatus.NO_ENTRY_WINDOW)
        session = self.panel.session_on(cycle.entry_day)
        quotes = contracts_on(self.panel.options_on(cycle.entry_day, cycle.expiry))
        if session is None or session.underlying is None or not quotes:
            # the panel has no entry-day data: no close, or no option rows (a day it left out keeps only index closes)
            return CycleResult(cycle, structure.code, CycleStatus.UNFILLABLE)
        trials: list[WidthTrial] = []
        for width in self.terms.widths:
            legs = structure.legs(frozenset(quotes), session.underlying, width)
            if legs is None:
                trials.append(WidthTrial(width, CycleStatus.MISSING_STRIKES))
                continue
            entry = [leg_price(quotes.get(leg.contract), cycle.entry_day) for leg in legs]
            trial = self._entry_trial(width, legs, entry)
            trials.append(trial)
            if trial.outcome == CycleStatus.TRADED:
                return self._exit(cycle, structure, legs, entry, tuple(trials))
        return CycleResult(cycle, structure.code, _no_trade_status(trials), tuple(trials))

    def _entry_trial(self, width: float, legs: list[Leg], entry: list[LegPrice]) -> WidthTrial:
        problem = fill_problem(entry)
        if problem:
            return WidthTrial(width, problem)
        prices = [p.price for p in entry]
        lowest, highest = payoff_bounds(legs)
        if not lowest < position_value(legs, prices) < highest:
            return WidthTrial(
                width, CycleStatus.BAD_PRICES
            )  # the prices promise a trade that cannot lose or cannot win
        loss = self.costs.max_loss(legs, prices)
        return WidthTrial(width, CycleStatus.TRADED if loss <= self.terms.cap else CycleStatus.NO_TRADE_CAP, loss)

    def _exit(
        self, cycle: Cycle, structure: Structure, legs: list[Leg], entry: list[LegPrice], trials: tuple[WidthTrial, ...]
    ) -> CycleResult:
        quotes = contracts_on(self.panel.options_on(cycle.exit_day, cycle.expiry))
        exit_ = [leg_price(quotes.get(leg.contract), cycle.exit_day) for leg in legs]
        chosen = trials[-1]
        results = tuple(LegResult(leg, e, x) for leg, e, x in zip(legs, entry, exit_, strict=True))
        if fill_problem(exit_):
            return CycleResult(
                cycle, structure.code, CycleStatus.UNFILLABLE, trials, chosen.width, results, max_loss=chosen.max_loss
            )
        entry_prices, exit_prices = [p.price for p in entry], [p.price for p in exit_]
        gross = self.costs.gross(legs, entry_prices, exit_prices)
        charges = self.costs.charges(legs, entry_prices, True) + self.costs.charges(legs, exit_prices, False)
        pads = self.costs.pads(legs)
        lowest, highest = payoff_bounds(legs)
        impossible = not lowest <= position_value(legs, exit_prices) <= highest
        return CycleResult(
            cycle, structure.code, CycleStatus.TRADED, trials, chosen.width, results,
            gross, charges, pads, gross - charges - pads, chosen.max_loss, impossible,
        )  # fmt: skip


def _no_trade_status(trials: Sequence[WidthTrial]) -> CycleStatus:
    """Why the search ended without a trade: the outcome of the narrowest listed width (wider widths only show that a
    narrower one had to be tried), or `missing_strikes` when no width was listed."""
    listed = [t.outcome for t in trials if t.outcome != CycleStatus.MISSING_STRIKES]
    return listed[-1] if listed else CycleStatus.MISSING_STRIKES
