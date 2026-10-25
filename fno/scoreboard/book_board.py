"""One book on scoreboard B (story S2, S1's `common_start`, `pilot_evidence` and `segments`). Every trade opened
before the common start is pilot evidence, reported apart and never head-to-head. From the common start on, the head-
to-head figures hold only scored trades that were not overridden, overall and per D6 segment. Unscored and overridden
trades are shown in their own sections. A trade stays in the segment of the decision that opened it to its end.
Operating costs are the book's, not a version's: they enter the book-level sections only."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from .book_trades import NO_RECORD, OVERRIDDEN, ScoredTrade, Sessions
from .do_nothing import DoNothing
from .ports import AiCostAllocation
from .random_control import RandomControl, RealTrade
from .sections import section
from .series import costs_by_session, daily_series, held_at_close
from .uncertainty import uncertainty

PILOT = "pilot, not counted"
AI_AT_BOOK_LEVEL = "charged at book level only (overall, pilot, head-to-head)"
COMMON_START_NOT_REACHED = "pilot, not counted: common start not reached, every figure is pilot evidence"


@dataclass(frozen=True)
class BookInputs:
    book: str
    trades: tuple[ScoredTrade, ...]
    operating_costs: tuple[dict, ...]  # C1's rows
    first: date  # the account's first session
    on: date


def full_months(first: date, last: date) -> int:
    """Whole calendar months from the month after `first` (unless it is the 1st) to the month of `last` if complete."""
    start = (first.year, first.month) if first.day == 1 else (first.year + (first.month == 12), first.month % 12 + 1)
    months = (last.year - start[0]) * 12 + last.month - start[1]
    return max(months, 0)


class BookBoard:
    def __init__(self, sessions: Sessions, ai: AiCostAllocation, brake_rs: float | None = None,
                 do_nothing: DoNothing | None = None, luck: RandomControl | None = None):  # fmt: skip
        self.sessions, self.ai, self.brake_rs, self.do_nothing = sessions, ai, brake_rs, do_nothing
        self.luck = luck

    def build(self, inputs: BookInputs, common_start: date | None) -> dict:
        monthly = _monthly(inputs.operating_costs)
        whole = (inputs.first, inputs.on)
        board = {"overall": self._section(inputs, inputs.trades, inputs.first, inputs.on, monthly, False, whole)}
        if common_start is None or common_start > inputs.on:
            board["pilot"] = board["overall"] | {"label": COMMON_START_NOT_REACHED}
            return board | {"head_to_head": None, "unscored": None, "overridden": None,
                            "strategies": self._strategies(inputs)}  # fmt: skip
        pilot = [t for t in inputs.trades if t.opened_on < common_start]
        later = [t for t in inputs.trades if t.opened_on >= common_start]
        before = {m: v for m, v in monthly.items() if m < common_start.strftime("%Y-%m")}
        pilot_ai = (inputs.first, common_start - timedelta(days=1))  # AI periods never overlap (judge 87)
        board["pilot"] = self._section(inputs, pilot, inputs.first, inputs.on, before, False, pilot_ai) | {
            "label": PILOT
        }
        scored = [t for t in later if t.group not in (NO_RECORD, OVERRIDDEN)]
        after = {m: v for m, v in monthly.items() if m >= common_start.strftime("%Y-%m")}
        board["head_to_head"] = self._section(
            inputs, scored, common_start, inputs.on, after, True, (common_start, inputs.on)
        )
        board["head_to_head"]["segments"] = {
            label: self._section(inputs, [t for t in scored if t.group == label], common_start, inputs.on, {}, True)
            for label in sorted({t.group for t in scored})
        }
        for name in (NO_RECORD, OVERRIDDEN):
            board[name] = self._section(
                inputs, [t for t in later if t.group == name], common_start, inputs.on, {}, False
            )
        board["strategies"] = self._strategies(inputs)
        return board

    def _strategies(self, inputs: BookInputs) -> dict:
        """One entry per playbook version this book traded, pilot included (story S6: the level RM1's gate reads; its
        closed trades and net equal E6's card for the account and version, both from C1's trade ledger)."""
        entries = {}
        for version in sorted({t.strategy for t in inputs.trades}):
            trades = [t for t in inputs.trades if t.strategy == version]
            closed = sorted(t.trade_id for t in trades if t.line is not None)
            entry = self._section(inputs, trades, inputs.first, inputs.on, {}, False)
            entries[version] = entry | {"closed_trade_ids": closed}
        return entries

    def _section(
        self, inputs: BookInputs, trades: Sequence[ScoredTrade], first: date, last: date, monthly: dict, judged: bool,
        ai_period: tuple[date, date] | None = None,
    ) -> dict:  # fmt: skip
        """`ai_period`: the days whose allocated AI cost this section carries; None for segments, unscored and
        overridden trades, whose AI cost stays at book level, so no rupee is counted twice."""
        sessions = self.sessions(first, last)
        costs = costs_by_session(monthly, sessions)
        series = daily_series(trades, costs, sessions)
        positions = sum(t.completed and t.line is not None for t in trades)
        judged_by = uncertainty(series, positions, full_months(first, last)) if judged else None
        if ai_period is None:
            # The AI cost is charged at book level only, so a part of the book has no share of it: its verdict stands
            # only when the book's whole AI cost is zero (Book 1), else it is unknown (no verdict), never counted twice.
            against = self._against(0.0 if self.ai.allocated(inputs.book, first, last) == 0 else None)
            board = section(trades, series, sum(costs.values()), 0.0, judged_by, first, last, self.brake_rs, against)
            return board | {"ai_cost_allocated_rs": AI_AT_BOOK_LEVEL} | self._luck(trades, series, judged)
        ai = self.ai.allocated(inputs.book, *ai_period)
        board = section(
            trades, series, sum(costs.values()), ai, judged_by, first, last, self.brake_rs, self._against(ai)
        )
        return board | self._luck(trades, series, judged)

    def _luck(self, trades: Sequence[ScoredTrade], series, judged: bool) -> dict:
        """The random control on judged sections only (story S6): every completed position with its record's shape."""
        if self.luck is None or not judged:
            return {}
        real = [RealTrade(t.structure, t.legs, t.units, t.opened_on, t.closed_on, t.line.net, t.entry.max_loss,
                          sum(held_at_close(t, d) for d in series.days))
                for t in trades if t.completed and t.line and t.entry and t.legs and t.structure]  # fmt: skip
        return {"random_control": self.luck.control(real)}

    def _against(self, cost: float | None):
        """The do-nothing comparison for a section (story S6) with its AI cost; None: unknown, so no verdict."""
        if self.do_nothing is None:
            return None
        return lambda series, capital, unrecorded: self.do_nothing.compare(series, capital, cost, unrecorded)


def _monthly(rows: Sequence[dict]) -> dict[str, float]:
    months: dict[str, float] = {}
    for row in rows:
        months[row["month"]] = months.get(row["month"], 0.0) + float(row["amount_rs"])
    return dict(sorted(months.items()))
