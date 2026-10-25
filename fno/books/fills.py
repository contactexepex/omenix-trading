"""One paper fill and its row in a book's append-only cash ledger (story E1).

A fill wraps the cost accountant's `Order` (story C1: side, quoted price, units, pad) so that the account and the three
ledgers price a fill the same way: cash moves by the fill price (quoted price made worse by the pad) times units, minus
every charge from `fno.costs` on that fill price. Deciding and pricing fills is E4's job; E1 only records them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..accounting.ledgers import Order
from ..constants import LEDGER_FILL, LEDGER_OPENING, LEDGER_SETTLEMENT, LEDGER_TOP_UP, SIDE_BUY, SIDES
from ..costs import CHARGE_NAMES

LEDGER_COLUMNS = (
    ("entry_id", "kind", "trade_id", "filled_at", "contract", "side", "units", "quoted_price", "pad", "fill_price")
    + tuple(CHARGE_NAMES)
    + ("charges_rs", "amount_rs", "cash_after_rs")
)
# Columns that identify what was filled; a repeated fill ID must repeat all of them, else it is a conflict.
FILL_IDENTITY = LEDGER_COLUMNS[: -3 - len(CHARGE_NAMES)] + tuple(CHARGE_NAMES)


class FillError(ValueError):
    """A fill that cannot be recorded as given."""


def _plain(name: str, value: str) -> str:
    if not value or any(ch in value for ch in "\r\n\x00") or value != value.strip():
        raise FillError(f"{name} must be non-empty single-line text without outer spaces: {value!r}")
    return value


@dataclass(frozen=True)
class Fill:
    fill_id: str  # unique per account, set by the filler; the idempotency key
    trade_id: str  # the trade (structure) this leg belongs to
    filled_at: datetime  # time zone aware
    contract: str  # the exchange's contract symbol, e.g. NIFTY25O2825000CE
    order: Order
    charges: dict[str, float] = field(default_factory=dict)  # by `fno.costs` component, on the fill price

    def __post_init__(self):
        _plain("fill_id", self.fill_id)
        _plain("trade_id", self.trade_id)
        _plain("contract", self.contract)
        if self.filled_at.tzinfo is None:
            raise FillError("filled_at must carry its time zone")
        if self.order.side not in SIDES or self.order.units <= 0 or int(self.order.units) != self.order.units:
            raise FillError(f"bad order {self.order}: side must be buy or sell and units a positive whole number")
        if self.order.quoted_price < 0 or self.order.pad < 0:
            raise FillError(f"bad order {self.order}: prices and pads cannot be negative")
        if set(self.charges) != set(CHARGE_NAMES):
            raise FillError(f"charges must list exactly {sorted(CHARGE_NAMES)}")

    @classmethod
    def priced(cls, fill_id: str, trade_id: str, filled_at: datetime, contract: str, order: Order, table: dict) -> Fill:
        """A fill with its charges from the one charges model (`fno.costs`), as C1 prices them (a cash settlement at
        expiry is charged as one, story E7)."""
        return cls(fill_id, trade_id, filled_at, contract, order, order.charges(table))

    @property
    def signed_units(self) -> int:
        return int(self.order.units) if self.order.side == SIDE_BUY else -int(self.order.units)

    @property
    def amount(self) -> float:
        """Cash change: premium received (sell) or paid (buy) at the fill price, minus all charges."""
        return -self.signed_units * self.order.fill_price - sum(self.charges.values())

    def ledger_row(self, cash_before: float) -> dict[str, str]:
        row = {
            "entry_id": self.fill_id,
            "kind": LEDGER_SETTLEMENT if self.order.settlement else LEDGER_FILL,
            "trade_id": self.trade_id,
            "filled_at": self.filled_at.isoformat(),
            "contract": self.contract,
            "side": self.order.side,
            "units": str(int(self.order.units)),
            "quoted_price": repr(float(self.order.quoted_price)),
            "pad": repr(float(self.order.pad)),
            "fill_price": repr(float(self.order.fill_price)),
        }
        row |= {name: repr(float(self.charges[name])) for name in CHARGE_NAMES}
        row["charges_rs"] = repr(float(sum(self.charges.values())))
        row["amount_rs"] = repr(self.amount)
        row["cash_after_rs"] = repr(cash_before + self.amount)
        return row

    @classmethod
    def from_row(cls, row: dict[str, str]) -> Fill:
        settled = row["kind"] == LEDGER_SETTLEMENT
        order = Order(row["side"], float(row["quoted_price"]), int(row["units"]), float(row["pad"]), settled)
        charges = {name: float(row[name]) for name in CHARGE_NAMES}
        return cls(row["entry_id"], row["trade_id"], datetime.fromisoformat(row["filled_at"]), row["contract"], order,
                   charges)  # fmt: skip


FILL_KINDS = (LEDGER_FILL, LEDGER_SETTLEMENT)  # ledger rows that move a position
CAPITAL_KINDS = (LEDGER_OPENING, LEDGER_TOP_UP)  # ledger rows that add capital: never a trade, never profit


def opening_row(entry_id: str, day: str, amount: float) -> dict[str, str]:
    """The first row of every account: the starting cash."""
    row = dict.fromkeys(LEDGER_COLUMNS, "")
    row |= {"entry_id": entry_id, "kind": LEDGER_OPENING, "filled_at": day}
    row |= {"amount_rs": repr(float(amount)), "cash_after_rs": repr(float(amount))}
    return row


def top_up_row(entry_id: str, written_at: datetime, amount: float, cash_before: float) -> dict[str, str]:
    """A capital top-up at its write instant (story E1b): time-zone aware, so it counts only from that instant."""
    if written_at.tzinfo is None:
        raise FillError("a top-up's write instant must carry its time zone")
    row = dict.fromkeys(LEDGER_COLUMNS, "")
    row |= {"entry_id": entry_id, "kind": LEDGER_TOP_UP, "filled_at": written_at.isoformat()}
    return row | {"amount_rs": repr(float(amount)), "cash_after_rs": repr(float(cash_before + amount))}


def same_fill(row: dict[str, str], fill: Fill) -> bool:
    """True when a recorded row is this exact fill (a retry); False when the ID was used for something else."""
    new = fill.ledger_row(0.0)
    return all(row[column] == new[column] for column in FILL_IDENTITY)
