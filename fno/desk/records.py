"""A book's desk records (story E4), beside its paper account in `journal/<book>/account/`:

- `desk_fills.csv`: one row per filled leg: book, decision ID, snapshot ID and hash, leg, side, price, size, every C1
  charge, `quote_age_unknown`. The touch it filled against is not written (owner "8 A", story E2b): E6 reads it from
  the hash-checked execution snapshot the row names. The money itself is E1's cash ledger, written with the same fill
  ID first.
- `desk_events.csv`: how each entry or exit attempt ended (opened, not opened, partial fill and its legging cost,
  exit ordered, pending exit, protection unverified, closed), so E3, E6 and the judge can replay a day.

Reading needs no lock (`DeskRecords`); writing goes through the book's held account writer (`DeskJournal`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..books.account import AccountWriter, PaperAccount
from ..books.fills import Fill
from ..costs import CHARGE_NAMES
from ..research_engine.structures import BOUGHT, SOLD, Leg
from .csv_log import IdempotentCsvLog
from .pricing import DeskLeg

FILLS_FILE, EVENTS_FILE = "desk_fills.csv", "desk_events.csv"
OPENING_SIDE = {BOUGHT: "bought", SOLD: "sold"}
FILL_COLUMNS = (
    ("fill_id", "book", "strategy", "decision_id", "trade_id", "action", "filled_at", "snapshot_id", "snapshot_sha256")
    + ("contract", "quote_contract_id", "expiry", "strike", "type", "opening_side", "side", "price", "units")
    + tuple(CHARGE_NAMES)
    + ("charges_rs", "quote_age_unknown")  # no quote_bid / quote_ask: owner "8 A" (story E2b)
)
# No shortfall_rs: with the approved limit it gives the net at the touch back (decision 45, story E2b).
EVENT_COLUMNS = (
    "event_id", "day", "book", "strategy", "trade_id", "decision_id", "snapshot_id", "snapshot_sha256", "outcome",
    "reason", "legging_cost_rs",
)  # fmt: skip


@dataclass(frozen=True)
class FillRecord:
    book: str
    strategy: str  # the playbook version the trade belongs to ("<name>-v<n>"; story E6 scores by it)
    decision_id: str
    action: str  # FILL_OPEN, FILL_UNWIND or FILL_CLOSE
    snapshot_id: str
    snapshot_sha256: str
    leg: DeskLeg
    quote_contract_id: str
    quote_age_unknown: bool
    fill: Fill  # E1's fill: trade, time, contract, order (side, price, units, pad) and C1's charges

    def row(self) -> dict[str, str]:
        fill, leg = self.fill, self.leg
        row = {
            "fill_id": fill.fill_id, "book": self.book, "strategy": self.strategy, "decision_id": self.decision_id,
            "trade_id": fill.trade_id, "action": self.action, "filled_at": fill.filled_at.isoformat(),
            "snapshot_id": self.snapshot_id, "snapshot_sha256": self.snapshot_sha256, "contract": fill.contract,
            "quote_contract_id": self.quote_contract_id, "expiry": leg.expiry.isoformat(),
            "strike": repr(float(leg.leg.strike)), "type": leg.leg.kind, "opening_side": OPENING_SIDE[leg.leg.side],
            "side": fill.order.side, "price": repr(float(fill.order.fill_price)), "units": str(int(fill.order.units)),
        }  # fmt: skip
        row |= {name: repr(float(fill.charges[name])) for name in CHARGE_NAMES}
        row |= {"charges_rs": repr(float(sum(fill.charges.values()))), "quote_age_unknown": str(self.quote_age_unknown)}
        return row


@dataclass(frozen=True)
class DeskEvent:
    event_id: str
    day: date
    book: str
    strategy: str
    trade_id: str
    decision_id: str
    snapshot_id: str
    snapshot_sha256: str
    outcome: str
    reason: str
    legging_cost_rs: float | None = None

    def row(self) -> dict[str, str]:
        values = (self.event_id, self.day.isoformat(), self.book, self.strategy, self.trade_id, self.decision_id,
                  self.snapshot_id, self.snapshot_sha256, self.outcome, self.reason,
                  _amount(self.legging_cost_rs))  # fmt: skip
        return dict(zip(EVENT_COLUMNS, values, strict=True))


def _amount(value: float | None) -> str:
    return "" if value is None else repr(float(value))


def leg_of(row: dict[str, str]) -> DeskLeg:
    """The leg a desk fill row was for, so an open position can be quoted again at a later snapshot."""
    side = BOUGHT if row["opening_side"] == OPENING_SIDE[BOUGHT] else SOLD
    return DeskLeg(row["contract"], date.fromisoformat(row["expiry"]), Leg(float(row["strike"]), row["type"], side))


class DeskRecords:
    """Read access to one book's desk records; every file is inside that book's own account folder (E1 firewall)."""

    def __init__(self, account: PaperAccount):
        self.account = account
        self.fills = IdempotentCsvLog(
            account.file(FILLS_FILE), account.file(FILLS_FILE + ".tmp"), FILL_COLUMNS, "fill_id"
        )
        self.events = IdempotentCsvLog(
            account.file(EVENTS_FILE), account.file(EVENTS_FILE + ".tmp"), EVENT_COLUMNS, "event_id"
        )

    def fill_rows(self, trade_id: str | None = None) -> list[dict[str, str]]:
        return [r for r in self.fills.rows() if trade_id is None or r["trade_id"] == trade_id]

    def event_rows(self, trade_id: str | None = None) -> list[dict[str, str]]:
        return [r for r in self.events.rows() if trade_id is None or r["trade_id"] == trade_id]

    def legs(self, trade_id: str) -> dict[str, DeskLeg]:
        """Contract -> leg, from the trade's opening fills."""
        return {r["contract"]: leg_of(r) for r in self.fill_rows(trade_id)}


class DeskJournal:
    """The only way to write desk records: each write checks the book's single-writer lock (E1) first."""

    def __init__(self, writer: AccountWriter):
        self.writer = writer
        self.records = DeskRecords(writer.account)

    def record_fill(self, record: FillRecord) -> bool:
        """The fill into E1's cash ledger, then its desk row; both idempotent by fill ID, so a rerun repeats nothing."""
        self.writer.require_lock()
        applied = self.writer.apply_fill(record.fill)
        written = self.records.fills.append(record.row())
        return applied or written

    def record_event(self, event: DeskEvent) -> bool:
        self.writer.require_lock()
        return self.records.events.append(event.row())
