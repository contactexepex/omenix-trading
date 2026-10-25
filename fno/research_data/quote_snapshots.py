"""The 3 pm quote snapshots of story A4 read back for live features (story B7): a day's canonical snapshot, with each
contract's bid, ask and validity, the spot at capture, when the capture finished, and (since the recorder reads them,
13 Oct 2026) India VIX and the NIFTY futures' last prices. Read-only; a day whose canonical marker is "none" or missing
has no snapshot; an older capture without levels has `vix` None and no futures."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime

from ..models import IST
from ..quotes.recorder import NONE_MARKER, QuoteSnapshotRecorder
from ..storage.raw_store import RawFileStore
from .panel_reader import FutureQuote

VALID = "true"


@dataclass(frozen=True)
class LiveQuote:
    expiry: date
    strike: float
    kind: str  # "CE" or "PE"
    bid: float | None
    ask: float | None
    valid: bool  # A4's validity: a same-day trade and a usable book
    contract_id: str = ""  # the provider's symbol as recorded (what the paper account names the contract by)

    @property
    def mid(self) -> float | None:
        """The midpoint of a valid two-sided quote; None otherwise (never the last price)."""
        if not self.valid or self.bid is None or self.ask is None or self.bid <= 0 or self.ask < self.bid:
            return None
        return (self.bid + self.ask) / 2


@dataclass(frozen=True)
class CutoffSnapshot:
    day: date
    finished_at: datetime  # IST, without a time zone: when the last quote of the capture arrived
    spot: float | None
    vix: float | None
    quotes: tuple[LiveQuote, ...]
    futures: tuple[FutureQuote, ...] = ()  # last price as `close`; no settlement (0.0) or open interest (0) at 3 pm

    def future_for(self, expiry: date) -> FutureQuote | None:
        return next((f for f in self.futures if f.expiry == expiry), None)

    def quotes_for(self, expiry: date) -> list[LiveQuote]:
        return [q for q in self.quotes if q.expiry == expiry]

    @property
    def expiries(self) -> list[date]:
        return sorted({q.expiry for q in self.quotes})


def _number(text: str) -> float | None:
    return float(text) if text else None


def _ist(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone(IST).replace(tzinfo=None)


def parse_snapshot(day: date, csv_bytes: bytes, meta_bytes: bytes) -> CutoffSnapshot:
    meta = json.loads(meta_bytes)
    quotes = tuple(
        LiveQuote(
            date.fromisoformat(row["expiry"]),
            float(row["strike"]),
            row["type"],
            _number(row["bid"]),
            _number(row["ask"]),
            row["valid"] == VALID,
            row.get("contract_id", ""),
        )  # fmt: skip
        for row in csv.DictReader(io.StringIO(csv_bytes.decode()))
    )
    futures = tuple(
        FutureQuote(date.fromisoformat(f["expiry"]), float(f["last"]), 0.0, int(f["volume"]), 0)
        for f in meta.get("futures", [])
    )
    return CutoffSnapshot(day, _ist(meta["finished_at"]), meta.get("spot"), meta.get("india_vix"), quotes, futures)


class RecordedSnapshots:
    """A4's quote store: the canonical snapshot of a day, if one was recorded."""

    def __init__(self, store: RawFileStore):
        self.store = store

    def snapshot(self, day: date) -> CutoffSnapshot | None:
        marker = self.store.get(QuoteSnapshotRecorder.path(day, f"nifty_{day:%Y%m%d}.canonical"))
        snapshot_id = marker.decode().strip() if marker else NONE_MARKER
        if snapshot_id == NONE_MARKER:
            return None
        csv_bytes = self.store.get(QuoteSnapshotRecorder.path(day, f"{snapshot_id}.csv"))
        meta_bytes = self.store.get(QuoteSnapshotRecorder.path(day, f"{snapshot_id}.meta.json"))
        return parse_snapshot(day, csv_bytes, meta_bytes) if csv_bytes and meta_bytes else None

    def snapshots(self, days) -> dict[date, CutoffSnapshot]:
        found = {day: self.snapshot(day) for day in days}
        return {day: s for day, s in found.items() if s is not None}
