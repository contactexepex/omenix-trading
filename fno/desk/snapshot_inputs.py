"""The day's canonical A4 quote snapshot as common-pack items (stories E2 and E2b). The committed pack holds no
per-contract quote figure (owner "8 A", decision B of 15 Oct 2026: a mid and a spread % would give bid and ask back
exactly on 0.05 ticks); readers read the raw rows through the hash-checked quote store, named by the provenance's
snapshot ID and both hashes. Kept: each monthly chain's NIFTY level (`spot:<expiry>`, an index level, available when the
chain's first row arrived), the capture's counts (`quote_counts`, available when its last row arrived), India VIX at the
later of NSE's own timestamp and the capture's first request (A4 reads it before any quote), and the futures' NSE levels
at that first request. A day without a canonical snapshot gives no items and says so in the provenance."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime

from ..models import IST
from ..quotes.recorder import NONE_MARKER, QuoteSnapshotRecorder
from ..storage.raw_store import RawFileStore
from .pack_inputs import CommonInput, InputBatch
from .pack_items import PackError, PackItem, available_time, sha256_hex

NSE_TIME_FORMATS = ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M")
SPOT_PREFIX, COUNTS_ITEM = "spot:", "quote_counts"
VALID = "true"  # A4's `valid` column


def _nse_time(text: str) -> datetime | None:
    for fmt in NSE_TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=IST)
        except ValueError:
            continue
    return None


def _spots(rows: list[dict], source: str, expiries: list[str], first_request: str) -> list[PackItem]:
    """One NIFTY level per monthly chain; a chain whose rows carry two levels is refused, never averaged. A chain the
    sidecar asked for (`expiries`) whose rows carry no level, or that has no rows at all, still gets its item, with no
    value, so C3 names it (one spot per recorded chain)."""
    chains: dict[str, list[dict]] = {expiry: [] for expiry in expiries}
    for row in rows:
        chains.setdefault(row["expiry"], []).append(row)
    items = []
    for expiry, chain in sorted(chains.items()):
        levels = {float(r["spot"]) for r in chain if r["spot"]}
        if len(levels) > 1:
            raise PackError(f"chain {expiry} carries {len(levels)} different spots {sorted(levels)}: nothing packed")
        # the level is known with the chain's first row; a chain without rows, at the capture's first request
        arrived = min((r["response_received_at"] for r in chain), default=first_request)
        level = levels.pop() if levels else None
        items.append(PackItem(f"{SPOT_PREFIX}{expiry}", level, f"{source} spot of chain {expiry}", arrived))
    return items


def _counts(rows: list[dict], meta: dict, source: str) -> PackItem:
    value = {
        "expected_contracts": meta.get("expected_contracts"),
        "recorded_contracts": meta.get("recorded_contracts"),
        "valid_contracts": sum(1 for r in rows if r["valid"] == VALID),
        "complete": bool(meta.get("complete")),
    }
    return PackItem(COUNTS_ITEM, value, f"{source} counts", max((r["response_received_at"] for r in rows), default=""))


class SnapshotInput(CommonInput):
    name = "a4_snapshot"

    def __init__(self, store: RawFileStore, dataset: str):
        self.store, self.dataset = store, dataset

    def collect(self, day: date) -> InputBatch:
        marker = self.store.get(QuoteSnapshotRecorder.path(day, f"nifty_{day:%Y%m%d}.canonical", self.dataset))
        snapshot_id = marker.decode().strip() if marker else NONE_MARKER
        csv_bytes, meta_bytes = (
            self.store.get(QuoteSnapshotRecorder.path(day, f"{snapshot_id}{suffix}", self.dataset))
            for suffix in (".csv", ".meta.json")
        )
        if snapshot_id == NONE_MARKER or not csv_bytes or not meta_bytes:
            return InputBatch((), {"dataset": self.dataset, "snapshot_id": None})
        rows = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"))))
        meta = json.loads(meta_bytes)
        source = f"a4 {self.dataset} {snapshot_id}"
        first_request = min((r["request_sent_at"] for r in rows), default="")
        items = _spots(rows, source, list(meta.get("expiries") or []), first_request) + [_counts(rows, meta, source)]
        items += self._vix(meta, source, first_request) + self._futures(meta, source, first_request)
        provenance = {"dataset": self.dataset, "snapshot_id": snapshot_id, "csv_sha256": sha256_hex(csv_bytes),
                      "meta_sha256": sha256_hex(meta_bytes)}  # fmt: skip
        return InputBatch(tuple(items), provenance)

    @staticmethod
    def _vix(meta: dict, source: str, first_request: str) -> list[PackItem]:
        stamp, value = _nse_time(str(meta.get("india_vix_time", ""))), meta.get("india_vix")
        if value is None:
            return []
        request = available_time(first_request)
        known = max(stamp, request).isoformat() if stamp and request else ""
        return [PackItem("india_vix", float(value), f"{source} meta india_vix (NSE timestamp)", known)]

    @staticmethod
    def _futures(meta: dict, source: str, first_request: str) -> list[PackItem]:
        return [
            PackItem(
                f"future:{f['expiry']}",
                {"last": float(f["last"]), "volume": int(f["volume"])},
                f"{source} meta futures",
                first_request,
            )  # fmt: skip
            for f in meta.get("futures", [])
        ]
