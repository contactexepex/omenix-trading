"""The handed-over entry's order, kept at the hand-over (judge 203 early view 1): the decided legs and units, the
approved entry cash (the price cap), the decision ID and when it was committed, exactly as E4 would have filled them
at 15:15. The owner-timing fill fills that order and nothing rebuilt the next day, so a market move, a playbook change
or a changed decision source can never change what fills; the fill day's C2 and C4 run is only a check on it.

One write-once file per account and trade in E8's own Drive records: written before the `entry_pending` event, so an
entry is never pending without its order, and the same order written again by a rerun changes nothing."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime

from ...research_engine.structures import Leg
from ...risk.inputs import Proposal, ProposedLeg, TradeTerms
from ...risk.manager import RiskDecision
from ...risk.verdict import RiskVerdict
from ...storage.raw_store import RawFileStore
from ..entries import EntryOrder
from .pending import OrderMissing, OrderSource, PendingEntry
from .timing_log import account_folder

ORDER_PATH = "{account}/orders/{trade_id}.json"
NOT_KEPT = "no order was kept for {book} trade {trade_id} at its hand-over"


def order_data(order: EntryOrder) -> bytes:
    proposal, risk = order.proposal, order.risk
    body = {
        "book": order.book, "strategy": order.strategy, "decision_id": order.decision_id,
        "decided_at": order.decided_at.isoformat(), "expiry": order.expiry.isoformat(),
        "proposal": {
            "trade_id": proposal.trade_id, "lot_size": proposal.lot_size,
            "terms": asdict(proposal.terms),
            "legs": [{"contract": p.contract, "strike": p.leg.strike, "kind": p.leg.kind, "side": p.leg.side}
                     for p in proposal.legs],
        },
        "risk": risk.record(),
    }  # fmt: skip
    return (json.dumps(body, indent=1, sort_keys=True) + "\n").encode()


def order_from(data: bytes) -> EntryOrder:
    body = json.loads(data)
    raw = body["proposal"]
    legs = tuple(ProposedLeg(p["contract"], Leg(p["strike"], p["kind"], p["side"])) for p in raw["legs"])
    proposal = Proposal(raw["trade_id"], TradeTerms(**raw["terms"]), raw["lot_size"], legs)
    risk = body["risk"]
    verdicts = tuple(RiskVerdict(v["rule"], v["ok"], v["reason"], v["numbers"]) for v in risk["verdicts"])
    decision = RiskDecision(risk["book"], risk["trade_id"], risk["day"], verdicts, risk["stressed_margin"],
                            tuple(risk["stale_marks"]), risk["entry_cash_rs"], proposal)  # fmt: skip
    return EntryOrder(body["book"], body["strategy"], body["decision_id"], datetime.fromisoformat(body["decided_at"]),
                      proposal, date.fromisoformat(body["expiry"]), decision)  # fmt: skip


class KeptOrders(OrderSource):
    def __init__(self, reader: RawFileStore, writer: RawFileStore):
        self.reader, self.writer = reader, writer

    def keep(self, order: EntryOrder) -> None:
        self.writer.put(self._path(order.book, order.proposal.trade_id), order_data(order))

    def order(self, pending: PendingEntry) -> EntryOrder:
        data = self.reader.get(self._path(pending.book, pending.trade_id))
        if not data:
            raise OrderMissing(NOT_KEPT.format(book=pending.book, trade_id=pending.trade_id))
        return order_from(data)

    @staticmethod
    def _path(book: str, trade_id: str) -> str:
        return ORDER_PATH.format(account=account_folder(book), trade_id=trade_id)
