"""C4's evidence (story C4): the raw A4 quote snapshot a decision was made on, read again from the store and accepted
only if it is the committed capture (C3's `CaptureRecord`: both files' SHA-256 equal), of the decision's day, started
before the decision cutoff. Rows are parsed here from the raw CSV, not through the desk's own snapshot reader. A quote
counts only if A4's rule finds it usable (`ExecutionQuote.a4_problem`, the one rule Book 1 prices by: two-sided, not
crossed, sizes on both sides, a trade today). An invalid quote has no mid for pricing (judge 83 addendum 2), so a bad
at-the-money quote cannot move the parity forward or any stress figure."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date, datetime

from ..desk.snapshot import quote_from_row
from ..quotes.recorder import QuoteSnapshotRecorder
from ..storage.raw_store import RawFileStore
from .data_checks import CaptureRecord

Key = tuple[str, float, str]  # (expiry ISO, strike, "CE" or "PE")


@dataclass(frozen=True)
class QuoteRow:
    contract: str
    bid: float | None
    ask: float | None
    received_at: datetime | None
    a4_problem: str = ""  # why A4's rule finds the quote unusable; empty when it is usable

    @property
    def mid(self) -> float | None:
        if self.a4_problem or self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / 2


@dataclass(frozen=True)
class Evidence:
    snapshot_id: str
    started_at: datetime
    rows: dict[Key, QuoteRow]
    spot: float | None = None  # the capture's spot (meta `spot`), the one D2 prices with; None when not recorded

    def mids(self) -> dict[str, tuple[Key, float]]:
        """Each contract with an A4-usable quote: its key and mid."""
        return {row.contract: (key, row.mid) for key, row in self.rows.items() if row.mid is not None}

    def atm_strike(self, expiry: str) -> float | None:
        """The expiry's ATM strike as C4 re-derives it: among strikes with an A4-usable quote, the one nearest spot,
        the lower on a tie (story STR1). None without a spot or a usable quote."""
        strikes = {strike for (day, strike, _), row in self.rows.items() if day == expiry and row.mid is not None}
        if self.spot is None or not strikes:
            return None
        return min(strikes, key=lambda strike: (abs(strike - self.spot), strike))


def _time(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text) if text else None
    except ValueError:
        return None


def _number(text: str) -> float | None:
    return float(text) if text else None


def _hash_problem(name: str, data: bytes, expected: str) -> list[str]:
    actual = hashlib.sha256(data).hexdigest()
    return [] if actual == expected else [f"{name} SHA-256 {actual[:12]} differs from the record's {expected[:12]}"]


def _key(row: dict) -> Key:
    return row["expiry"], float(row["strike"]), row["type"]


def _row(row: dict) -> QuoteRow:
    problem = quote_from_row(row).a4_problem
    return QuoteRow(
        row["contract_id"], _number(row["bid"]), _number(row["ask"]), _time(row["response_received_at"]), problem
    )


class EvidenceReader:
    def __init__(self, store: RawFileStore, dataset: str):
        self.store, self.dataset = store, dataset

    def read(self, day: date, record: CaptureRecord | None) -> tuple[Evidence | None, list[str]]:
        """(the evidence, []) or (None, why it cannot be trusted)."""
        if record is None:
            return None, ["no committed capture record names the decision's snapshot"]
        csv_bytes, meta_bytes = (
            self.store.get(QuoteSnapshotRecorder.path(day, f"{record.snapshot_id}{suffix}", self.dataset))
            for suffix in (".csv", ".meta.json")
        )
        if not csv_bytes or not meta_bytes:
            return None, [f"snapshot {record.snapshot_id} of {day} is missing from the store"]
        problems = _hash_problem("quote file", csv_bytes, record.csv_sha256)
        problems += _hash_problem("meta file", meta_bytes, record.meta_sha256)
        if problems:
            return None, problems
        meta = json.loads(meta_bytes)
        rows = {_key(r): _row(r) for r in csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))}
        spot = meta.get("spot")
        return Evidence(record.snapshot_id, datetime.fromisoformat(meta["started_at"]), rows, spot), []
