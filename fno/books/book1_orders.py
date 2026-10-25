"""Book 1's committed decision turned into entry orders (story E5, E3's `OrderBuilder` seam). The run is replayed
through D2's own evaluator on its stored inputs (D3's replay, refused under other code): it must give exactly the
stored records, and its chosen outcomes then carry C2's decision with the exact proposal it judged. So an order is
never rebuilt from JSON by hand, and the entry limit is C2's own. Each order's `decision_id` is its D3 record's
opportunity ID, where E3 reads C4's recorded pass. The trade terms of Book 1's open trades come from the same
records, for C2's view of the book."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from ..desk.daily_ports import OrderBuilder, OrdersRefused
from ..desk.entries import EntryOrder
from ..desk.trade_counts import version_tag
from ..playbook.code_tree import CodeTree
from ..playbook.decision_inputs import DayInputs
from ..playbook.decision_run import ReplayRefused, replay
from ..playbook.decision_store import INPUTS_FILE, record_file
from ..playbook.decision_validity import TradeValidator
from ..playbook.evaluate import RuleEvaluator
from ..playbook.exit_terms import unenforceable_exits

NOT_REPLAYED = "{run}: the stored decision does not replay ({differences}); nothing is ordered"
TRADE = "trade"
NOT_ENFORCEABLE = "{run}: {version} states exits code cannot enforce ({what}); nothing is ordered"


class ReplayedOrders(OrderBuilder):
    """`validator` is C4's, as the decision run used it: the replay then reproduces each record's `validity.c4` too,
    and only opportunities whose committed record says "trade" (not blocked by C4) are ordered."""

    def __init__(self, evaluator: RuleEvaluator, code: CodeTree, validator: TradeValidator | None = None):
        self.evaluator, self.code, self.validator = evaluator, code, validator

    def orders(self, book: str, run: Path, decided_at: datetime) -> Sequence[EntryOrder]:
        try:
            differences = replay(run, self.evaluator, self.code, validator=self.validator)
        except ReplayRefused as refused:  # e.g. code merged after the decision: entries fail closed (judge 84)
            raise OrdersRefused(str(refused)) from refused
        if differences:
            raise OrdersRefused(NOT_REPLAYED.format(run=run.name, differences="; ".join(differences[:3])))
        inputs = DayInputs.from_json(json.loads((run / INPUTS_FILE).read_bytes()))
        evaluation = self.evaluator.evaluate(*inputs.replay_arguments())
        traded = [o for o in evaluation.chosen if _stored_action(run, o.opportunity.opportunity_id) == TRADE]
        for outcome in traded:
            unenforced = unenforceable_exits(outcome.opportunity.strategy)
            if unenforced:
                version = version_tag(outcome.opportunity.strategy.name, outcome.opportunity.strategy.version)
                raise OrdersRefused(NOT_ENFORCEABLE.format(run=run.name, version=version, what="; ".join(unenforced)))
        return [
            EntryOrder(book, version_tag(o.opportunity.strategy.name, o.opportunity.strategy.version),
                       o.opportunity.opportunity_id, decided_at, o.risk.proposal, o.opportunity.context.expiry, o.risk)
            for o in traded
        ]  # fmt: skip


def _stored_action(run: Path, opportunity_id: str) -> str | None:
    """The committed record's `chosen_action` for the opportunity (a C4-blocked choice says "no trade")."""
    path = run / record_file(opportunity_id)
    return json.loads(path.read_text(encoding="utf-8")).get("chosen_action") if path.is_file() else None
