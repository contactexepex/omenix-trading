"""One scorecard: a strategy version in one account, against its own evaluation plan (story E6).

Money comes from C1's three ledgers over the version's closed trades (operating costs are the desk's, not a version's,
so none are allocated here; the tax line is C1's assumed scenario on this version alone). Open positions are shown at
the marks of a snapshot (mid of valid quotes; none when a leg has no valid quote) and never counted in the results or
the review."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from ..accounting.ledgers import Ledgers, TradeLine
from ..desk.snapshot import ContractKey, ExecutionSnapshot, ExecutionSnapshotSource
from ..playbook.measurement import is_measurement
from ..playbook.schema import Strategy
from .execution_costs import ExecutionCosts, execution_costs
from .review import Review, ReviewTerms, review
from .strategy_record import OpenTrade, StrategyRecord

NO_VERSION = "not in the playbook: no plan to judge against"


@dataclass(frozen=True)
class OpenMark:
    trade_id: str
    cash_flow: float
    marked_net: float | None  # cash flow plus the legs at mid; None when a leg has no valid quote (never guessed)


@dataclass(frozen=True)
class Scorecard:
    account: str
    strategy: str
    status: str
    expected_range: tuple[float, float] | None
    unit: str
    trade_lines: tuple[TradeLine, ...]  # C1's trade ledger, every closed trade (unwound entries included)
    by_month: dict
    tax_by_year: dict
    costs: ExecutionCosts
    review: Review | None
    open_marks: tuple[OpenMark, ...]
    measurement: bool = False  # story R3: a measurement version, labelled wherever it is shown

    @property
    def total_net(self) -> float:
        return sum(line.net for line in self.trade_lines)


def snapshot_marks(snapshot: ExecutionSnapshot) -> dict[ContractKey, float]:
    """Mid of every valid two-sided quote: the only marks a scorecard uses."""
    return {key: (q.bid + q.ask) / 2 for key, q in snapshot.quotes.items() if q.valid and q.bid and q.ask}


def _mark(trade: OpenTrade, marks: Mapping[ContractKey, float]) -> OpenMark:
    value = 0.0
    for leg, units in trade.holdings:
        mid = marks.get((leg.expiry, float(leg.leg.strike), leg.leg.kind))
        if mid is None:
            return OpenMark(trade.trade_id, trade.cash_flow, None)
        value += leg.leg.side * units * mid
    return OpenMark(trade.trade_id, trade.cash_flow, trade.cash_flow + value)


def build_scorecard(
    record: StrategyRecord,
    strategy: Strategy | None,
    on: date,
    marks: Mapping[ContractKey, float],
    terms: ReviewTerms,
    snapshots: ExecutionSnapshotSource,
) -> Scorecard:
    lines = tuple(t.line for t in record.closed)
    ledgers = Ledgers(list(lines), [], {})
    total = sum(line.net for line in lines)
    plan = strategy.evaluation_plan if strategy else None
    nets = [t.line.net for t in record.positions]
    judged = review(nets, total, record.first_entry, plan, on, terms) if plan else None
    return Scorecard(
        record.account, record.strategy, str(strategy.status) if strategy else NO_VERSION,
        plan["expected_range"] if plan else None, plan["unit"] if plan else "", lines, ledgers.by_month(),
        ledgers.tax_by_year(), execution_costs(record, on, snapshots), judged,
        tuple(_mark(t, marks) for t in record.open), is_measurement(strategy),
    )  # fmt: skip
