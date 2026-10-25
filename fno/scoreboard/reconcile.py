"""Story S2, criterion 2: a book's account net reconciles with C1's three ledgers to the rupee. The closed trades' net
in E1's cash ledger (what each trade's fills moved, charges included) must equal C1's trade ledger recomputed from the
same fills, and C1's account ledger (trade net by month minus operating costs) must add up to both and agree with
itself (`Ledgers.reconciles`). The cash ledger's balance must equal its opening plus every fill."""

from __future__ import annotations

from collections.abc import Sequence

from ..accounting.ledgers import Ledgers
from ..books.account import PaperAccount
from ..books.equity import trade_positions
from .book_trades import ScoredTrade
from .sections import rupees

RUPEE = 0.5  # "to the rupee": the difference rounds to zero rupees


def reconciliation(account: PaperAccount, trades: Sequence[ScoredTrade], operating_costs: Sequence[dict]) -> dict:
    positions = trade_positions(account.fills())
    closed = [t for t in trades if t.line]
    account_net = sum(positions[t.trade_id].cash_flow for t in closed)
    lines = [t.line for t in closed]
    # Deductibility only shapes C1's tax table, which scoreboard B does not report; the month table ignores it.
    ledgers = Ledgers(lines, list(operating_costs), {row["category"]: False for row in operating_costs})
    months = ledgers.by_month()
    trade_net = sum(line.net for line in lines)
    costs = sum(float(row["amount_rs"]) for row in operating_costs)
    rows = account.ledger_rows()
    balance = float(rows[-1]["cash_after_rs"]) - account.capital()  # capital is never part of the trades (E1b)
    checks = {
        "trade_ledger": abs(account_net - trade_net) < RUPEE,
        "account_ledger": abs(sum(m["account_result"] for m in months.values()) - (account_net - costs)) < RUPEE,
        "ledgers_agree": ledgers.reconciles(),
        "cash_ledger": abs(balance - sum(f.amount for f in account.fills())) < RUPEE,
    }
    return {
        "account_closed_net_rs": rupees(account_net), "trade_ledger_net_rs": rupees(trade_net),
        "operating_costs_rs": rupees(costs), "cash_change_rs": rupees(balance),
        "months": {m: {k: rupees(v) for k, v in values.items()} for m, values in months.items()},
        "checks": checks, "ok": all(checks.values()),
    }  # fmt: skip
