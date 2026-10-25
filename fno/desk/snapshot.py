"""The execution snapshot a paper fill is priced from (story E4): one A4 recorder capture, read by its ID, with each
contract's bid, ask, sizes and A4 validity, and the SHA-256 that every fill row carries.

The hash is checked against the one the recorder wrote in the capture's meta file: a changed or swapped quote file is
refused, never priced. Groww gives no quote timestamp, so a quote without one is marked `quote_age_unknown` (A4).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime

from ..constants import SIDE_BUY
from ..models import IST
from ..quotes.recorder import DATASET, QuoteSnapshotRecorder
from ..storage.raw_store import RawFileStore

VALID = "true"  # A4's `valid` column

ContractKey = tuple[date, float, str]  # (expiry, strike, "CE" or "PE")


class SnapshotError(ValueError):
    """A snapshot that cannot be priced from: missing, its hash not matching, or another day's."""


@dataclass(frozen=True)
class ExecutionQuote:
    contract_id: str  # the provider's symbol, as recorded (may be empty in fixtures)
    expiry: date
    strike: float
    kind: str
    bid: float | None
    ask: float | None
    bid_qty: float | None  # units at the best bid
    ask_qty: float | None  # units at the best ask
    valid: bool  # A4: two-sided, not crossed, sizes on both sides, a trade in the contract today
    invalid_reason: str
    quote_age_unknown: bool  # the provider gave no quote timestamp (Groww)

    @property
    def a4_problem(self) -> str:
        """Why this quote is not usable by A4's rule, or empty: bid > 0, ask > 0, bid <= ask, both sizes > 0, and a
        trade in the contract today (the recorder's `valid`, which holds that evidence). Its age is never claimed."""
        if not self.bid or self.bid <= 0 or not self.ask or self.ask <= 0:
            return "one-sided or empty book"
        if self.bid > self.ask:
            return "crossed (bid above ask)"
        if not self.bid_qty or self.bid_qty <= 0 or not self.ask_qty or self.ask_qty <= 0:
            return "no size"
        if not self.valid:
            return self.invalid_reason or "not valid by A4's rule (no trade today)"
        return ""

    def touch(self, side: str) -> tuple[float | None, float | None]:
        """Price and size a market order of this side meets: the ask for a buy, the bid for a sell."""
        return (self.ask, self.ask_qty) if side == SIDE_BUY else (self.bid, self.bid_qty)


@dataclass(frozen=True)
class ExecutionSnapshot:
    day: date
    snapshot_id: str
    sha256: str  # of the quote file, as the recorder wrote it
    meta_sha256: str  # of its sidecar (capture times, completeness), as read
    started_at: datetime  # time zone aware
    finished_at: datetime  # time zone aware: when the last quote of the capture arrived
    complete: bool  # A4: every expected contract recorded, no failure
    quotes: Mapping[ContractKey, ExecutionQuote]

    def quote(self, expiry: date, strike: float, kind: str) -> ExecutionQuote | None:
        return self.quotes.get((expiry, float(strike), kind))


def _number(text: str) -> float | None:
    return float(text) if text else None


def quote_from_row(row: dict[str, str]) -> ExecutionQuote:
    """One recorded A4 row as a quote; C4 reads its rows through this too (one A4 validity rule)."""
    return ExecutionQuote(
        row["contract_id"],
        date.fromisoformat(row["expiry"]),
        float(row["strike"]),
        row["type"],
        _number(row["bid"]),
        _number(row["ask"]),
        _number(row["bid_qty"]),
        _number(row["ask_qty"]),
        row["valid"] == VALID,
        row["invalid_reason"],
        not row["quote_time"],
    )


def _aware(text: str) -> datetime:
    moment = datetime.fromisoformat(text)
    return moment if moment.tzinfo else moment.replace(tzinfo=IST)


def parse_execution_snapshot(day: date, snapshot_id: str, csv_bytes: bytes, meta_bytes: bytes) -> ExecutionSnapshot:
    meta = json.loads(meta_bytes)
    digest = hashlib.sha256(csv_bytes).hexdigest()
    if meta.get("csv_sha256") != digest:
        raise SnapshotError(f"{snapshot_id}: quote file hash {digest} does not match its meta {meta.get('csv_sha256')}")
    if meta.get("snapshot_id") != snapshot_id:
        raise SnapshotError(f"{snapshot_id}: meta names snapshot {meta.get('snapshot_id')}")
    started, finished = _aware(meta["started_at"]), _aware(meta["finished_at"])
    if started.astimezone(IST).date() != day:
        raise SnapshotError(f"{snapshot_id}: captured on {started.date()}, not {day}")
    quotes = {}
    for row in csv.DictReader(io.StringIO(csv_bytes.decode())):
        quote = quote_from_row(row)
        key = (quote.expiry, quote.strike, quote.kind)
        if key in quotes:
            raise SnapshotError(f"{snapshot_id}: {key} recorded twice")
        quotes[key] = quote
    sidecar = hashlib.sha256(meta_bytes).hexdigest()
    return ExecutionSnapshot(day, snapshot_id, digest, sidecar, started, finished, bool(meta.get("complete")), quotes)


class ExecutionSnapshotSource(ABC):
    @abstractmethod
    def snapshot(self, day: date, snapshot_id: str) -> ExecutionSnapshot:
        """The named capture of that day; `SnapshotError` when it is missing or fails its checks."""


class RecordedExecutionSnapshots(ExecutionSnapshotSource):
    """A4's quote store: any capture of a day by its ID (E3's execution capture is not the 3 pm canonical one)."""

    def __init__(self, store: RawFileStore, dataset: str = DATASET):
        self.store, self.dataset = store, dataset

    def snapshot(self, day: date, snapshot_id: str) -> ExecutionSnapshot:
        try:
            csv_bytes = self.store.get(QuoteSnapshotRecorder.path(day, f"{snapshot_id}.csv", self.dataset))
            meta_bytes = self.store.get(QuoteSnapshotRecorder.path(day, f"{snapshot_id}.meta.json", self.dataset))
        except Exception as exc:  # A4b: the quote file is read from Drive; a failed read is a gate refusal, alerted
            raise SnapshotError(f"snapshot {snapshot_id} of {day} could not be read: {type(exc).__name__}") from exc
        if not csv_bytes or not meta_bytes:
            raise SnapshotError(f"snapshot {snapshot_id} of {day} is not in the quote store")
        return parse_execution_snapshot(day, snapshot_id, csv_bytes, meta_bytes)
