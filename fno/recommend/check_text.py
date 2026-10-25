"""The check's #fno-desk words (story REC1c): what the day's answer turned out to cost or save, after costs, with the
counts behind it. An incomplete day says why and gives no total; a day with no closed trade says abstaining cost
nothing."""

from __future__ import annotations

from .check_record import CandidateState, CheckRecord, Verdict
from .constants import PaperAnswer
from .contracts import Recommendation

FAILED = "The check failed: {problem}; no total is given."
INCOMPLETE = "Incomplete: {sources} unavailable at decision time, so there is no full total."
TRADED = "The recommended paper trade of {version} made Rs {net:,.2f} after costs."
NOTHING_TRADED = "No candidate traded, so abstaining cost nothing."
SAVED = "Its candidates' closed trades made Rs {total:,.2f} after costs, so abstaining saved Rs {amount:,.2f}."
COST = "Its candidates' closed trades made Rs {total:,.2f} after costs, so abstaining cost Rs {amount:,.2f}."
COUNTS = "({closed} closed, {open} open, {quiet} no trade, {tickets} ticket(s))."


def answer_text(record: Recommendation, check: CheckRecord) -> str:
    if check.verdict is Verdict.DATA_CHECK_FAILED:
        return FAILED.format(problem=check.problem)
    if check.verdict is Verdict.INCOMPLETE:
        return INCOMPLETE.format(sources=", ".join(check.unavailable_sources))
    if record.paper is PaperAnswer.PAPER_TRADE:
        key = (record.paper_trade.version, record.paper_trade.decision.path)
        net = next(r.net for r in check.results if (r.version, r.decision_path) == key)
        return TRADED.format(version=record.paper_trade.version, net=net)
    if not any(r.state is CandidateState.CLOSED for r in check.results):
        return NOTHING_TRADED
    total = check.closed_so_far  # final here, so the day's total
    return (SAVED if total < 0 else COST).format(total=total, amount=abs(total))


def trades_text(check: CheckRecord) -> str:
    counts = {state: sum(r.state is state for r in check.results) for state in CandidateState}
    return COUNTS.format(closed=counts[CandidateState.CLOSED], open=counts[CandidateState.OPEN],
                         quiet=counts[CandidateState.NO_TRADE], tickets=counts[CandidateState.TICKET])  # fmt: skip
