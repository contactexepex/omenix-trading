"""The shadow results adapter (story R1c, agreed with R3's owner, 16 Oct 2026): a shadow account's completed
positions opened after its freeze day (judge 271), net after C1's costs, read through E6's `strategy_records` from the
account's own desk records. The accounts live in Drive (E2c): the caller downloads them first
(`download_private_records`). No CSV is parsed here."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date

from ..constants import SHADOW_PREFIX
from ..desk.records import DeskRecords
from ..scorecard.strategy_record import strategy_records


class StrategyNets:
    def __init__(self, records_of: Callable[[str], DeskRecords], charges: Mapping[str, float]):
        self.records_of, self.charges = records_of, charges

    def nets(self, account: str, opened_after: date) -> list[float]:
        version = account.removeprefix(SHADOW_PREFIX)
        records = strategy_records(account, self.records_of(account), self.charges)
        positions = [t for r in records if r.strategy == version for t in r.positions if t.opened_on > opened_after]
        return [t.line.net for t in sorted(positions, key=lambda t: (t.opened_on, t.trade_id))]
