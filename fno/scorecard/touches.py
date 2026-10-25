"""The half-spread paid per unit (story E6 criterion 3), from the touch each fill was priced against (story E2b: the
fill rows no longer carry the bid and ask, owner "8 A"). The touch is read from the execution snapshot the row names,
through the hash-checked quote store, and the snapshot's SHA-256 must equal the row's `snapshot_sha256`. A fill whose
snapshot cannot be read, whose hash differs or whose contract has no two-sided quote there is "touch unknown":
counted and reported, left out of the average, never taken as zero. A settlement (no quote) is left out as before."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from ..constants import FILL_SETTLE, SIDE_BUY
from ..desk.snapshot import ExecutionSnapshot, ExecutionSnapshotSource, SnapshotError
from ..models import IST


@dataclass(frozen=True)
class HalfSpread:
    units: int  # units traded at a known touch
    per_unit: float | None  # None when no unit had a known touch
    touch_unknown: int  # fills (rows) whose touch could not be read


def half_spread(fills: Sequence[dict], snapshots: ExecutionSnapshotSource) -> HalfSpread:
    units, paid, unknown, cache = 0, 0.0, 0, {}
    for row in fills:
        if row["action"] == FILL_SETTLE:
            continue
        mid = _mid(row, snapshots, cache)
        if mid is None:
            unknown += 1
            continue
        price, size = float(row["price"]), int(row["units"])
        paid += (price - mid if row["side"] == SIDE_BUY else mid - price) * size
        units += size
    return HalfSpread(units, paid / units if units else None, unknown)


def _mid(row: dict, snapshots: ExecutionSnapshotSource, cache: dict) -> float | None:
    day = datetime.fromisoformat(row["filled_at"]).astimezone(IST).date()
    snapshot = _snapshot(day, row["snapshot_id"], snapshots, cache)
    if snapshot is None or snapshot.sha256 != row["snapshot_sha256"]:
        return None
    quote = snapshot.quotes.get((date.fromisoformat(row["expiry"]), float(row["strike"]), row["type"]))
    if quote is None or quote.bid is None or quote.ask is None:
        return None
    if row["quote_contract_id"] and quote.contract_id and quote.contract_id != row["quote_contract_id"]:
        return None
    return (quote.bid + quote.ask) / 2


def _snapshot(day: date, snapshot_id: str, snapshots: ExecutionSnapshotSource, cache: dict) -> ExecutionSnapshot | None:
    key = (day, snapshot_id)
    if key not in cache:
        try:
            cache[key] = snapshots.snapshot(day, snapshot_id)
        except (SnapshotError, ValueError, KeyError, OSError):  # one bad snapshot is one "touch unknown", never a crash
            cache[key] = None
    return cache[key]
