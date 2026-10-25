"""One road's canonical 3 pm capture of a session, read from the quote store and checked (story 3.5): the canonical
marker, its sidecar, the quote file's SHA-256 against the sidecar's, and the rows. The first thing wrong is the road's
one closure reason, in the story's order: missing, incomplete, out of window, hash mismatch, expiry mismatch. Two
checks need the quote file (it missing, and its row count), so they come after the sidecar's own window check.

A store that is down or unset (`RawQuoteStoreUnavailable`) is not a property of the capture: it propagates, and the
road is never closed for it."""

import csv
import hashlib
import io
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType

from ...quotes.drive_only_store import RawQuoteHashMismatch, RawQuoteMissing
from ...quotes.recorder import NONE_MARKER, QuoteSnapshotRecorder
from ...storage.raw_store import RawFileStore
from ..constants import ClosureReason, OptionKind
from ..contracts.roads import Road
from ..contracts.snapshot import ContractKey, SlotQuote, SlotSnapshot
from ..quality.rules import window_problem
from ..quality.strikes import strike_steps

NOT_ENOUGH_STRIKES = "an expiry with fewer than two strikes: no strike step"


class CaptureProblem(Exception):
    """The capture cannot be used; `reason` is the road's closure reason, `detail` says what was found."""

    def __init__(self, reason: ClosureReason, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else str(reason))
        self.reason, self.detail = reason, detail


@dataclass(frozen=True)
class Capture:
    road: Road
    session: date
    snapshot_id: str
    sha256: str
    started_at: datetime
    finished_at: datetime
    spot: float
    quotes: dict[ContractKey, SlotQuote]

    @property
    def expiries(self) -> tuple[date, ...]:
        return tuple(sorted({key.expiry for key in self.quotes}))

    def strike_steps(self) -> dict[date, float]:
        """Each recorded expiry's own strike step (`quality.strikes.strike_steps`); every expiry must have one."""
        steps = strike_steps(self.quotes)
        if set(steps) != set(self.expiries):
            raise CaptureProblem(ClosureReason.CAPTURE_INCOMPLETE, NOT_ENOUGH_STRIKES)
        return steps

    def strike_step(self) -> float:
        """The nearest expiry's strike step (`RoadDay.strike_step`)."""
        return self.strike_steps()[self.expiries[0]]

    def snapshot(self) -> SlotSnapshot:
        return SlotSnapshot(self.road.code, self.session, self.snapshot_id, self.sha256, self.started_at,
                            self.finished_at, self.spot, self.expiries, MappingProxyType(self.quotes))  # fmt: skip


class CaptureReader:
    """Reads and verifies each (road, session) once; a capture, or a fault in it, is kept for the run. A capture that is
    missing is asked for again, since it may still be recorded."""

    def __init__(self, stores: Mapping[str, RawFileStore]):
        """`stores`: the quote store of each road dataset (A4b keeps one Drive-only store per dataset)."""
        self.stores = stores
        self._found: dict[tuple, Capture | CaptureProblem] = {}

    def read(self, road: Road, session: date) -> Capture:
        """The verified capture, or `CaptureProblem` with the closure reason."""
        if (road.code, session) not in self._found:
            try:
                self._found[road.code, session] = self._load(road, session)
            except CaptureProblem as problem:
                if problem.reason is ClosureReason.CAPTURE_MISSING:
                    raise  # not final: the capture may land later in a long run
                self._found[road.code, session] = problem
        found = self._found[road.code, session]
        if isinstance(found, CaptureProblem):
            raise found
        return found

    def _get(self, road: Road, session: date, name: str) -> bytes | None:
        return self.stores[road.dataset].get(QuoteSnapshotRecorder.path(session, name, road.dataset))

    def _load(self, road: Road, session: date) -> Capture:
        marker = self._get(road, session, f"{road.stem}_{session:%Y%m%d}.canonical")
        snapshot_id = marker.decode().strip() if marker else NONE_MARKER
        if snapshot_id == NONE_MARKER:
            raise CaptureProblem(ClosureReason.CAPTURE_MISSING, "no canonical capture")
        sidecar = self._get(road, session, f"{snapshot_id}.meta.json")
        if sidecar is None:
            raise CaptureProblem(ClosureReason.CAPTURE_MISSING, f"{snapshot_id} has no sidecar")
        meta = _meta(sidecar)
        if meta.get("snapshot_id") != snapshot_id or meta.get("underlying") != road.underlying:
            raise CaptureProblem(ClosureReason.CAPTURE_INCOMPLETE, "the sidecar is another capture's")
        started, finished = _times(meta)
        if window_problem(road.code, session, started, finished) or meta.get("in_window") is not True:
            raise CaptureProblem(ClosureReason.OUT_OF_WINDOW, "outside the recorder's window")
        data = self._quote_file(road, session, snapshot_id)
        if hashlib.sha256(data).hexdigest() != meta.get("csv_sha256"):
            raise CaptureProblem(ClosureReason.HASH_MISMATCH, "quote file does not match its sidecar")
        quotes = _rows(data, meta)
        return Capture(road, session, snapshot_id, meta["csv_sha256"], started, finished, float(meta["spot"]), quotes)

    def _quote_file(self, road: Road, session: date, snapshot_id: str) -> bytes:
        try:
            data = self._get(road, session, f"{snapshot_id}.csv")
        except RawQuoteMissing as error:
            raise CaptureProblem(ClosureReason.CAPTURE_MISSING, str(error)) from error
        except RawQuoteHashMismatch as error:
            raise CaptureProblem(ClosureReason.HASH_MISMATCH, str(error)) from error
        if data is None:
            raise CaptureProblem(ClosureReason.CAPTURE_MISSING, f"{snapshot_id} has no quote file")
        return data


def _meta(sidecar: bytes) -> dict:
    """The sidecar of a complete capture; anything else is `capture_incomplete`, before its quote file is fetched."""
    try:
        meta = json.loads(sidecar)
        spot = float(meta["spot"])
        complete = (meta["complete"] is True and not meta["failures"] and math.isfinite(spot) and spot > 0
                    and meta["recorded_contracts"] == meta["expected_contracts"] > 0)  # fmt: skip
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        raise CaptureProblem(ClosureReason.CAPTURE_INCOMPLETE, f"sidecar unreadable: {error}") from error
    if not complete:
        raise CaptureProblem(ClosureReason.CAPTURE_INCOMPLETE, "the recorder did not mark it complete")
    return meta


def _times(meta: dict) -> tuple[datetime, datetime]:
    try:
        started, finished = (datetime.fromisoformat(meta[key]) for key in ("started_at", "finished_at"))
        if started.tzinfo is None or finished.tzinfo is None or finished < started:
            raise ValueError("times need a zone and an order")
    except (ValueError, KeyError, TypeError) as error:
        raise CaptureProblem(ClosureReason.CAPTURE_INCOMPLETE, f"sidecar times unreadable: {error}") from error
    return started, finished


def _rows(data: bytes, meta: dict) -> dict[ContractKey, SlotQuote]:
    try:
        quotes = {_key(row): _quote(row) for row in csv.DictReader(io.StringIO(data.decode()))}
        expiries = {str(expiry) for expiry in meta["expiries"]}
    except (ValueError, KeyError, TypeError, OverflowError, csv.Error) as error:
        raise CaptureProblem(ClosureReason.CAPTURE_INCOMPLETE, f"quote file unreadable: {error}") from error
    if len(quotes) != meta["recorded_contracts"]:
        raise CaptureProblem(ClosureReason.CAPTURE_INCOMPLETE, "rows differ from the sidecar's count")
    if {key.expiry.isoformat() for key in quotes} != expiries:
        raise CaptureProblem(ClosureReason.EXPIRY_MISMATCH, "rows name other expiries than the sidecar")
    return quotes


def _finite(cell: str) -> float:
    value = float(cell)
    if not math.isfinite(value):
        raise ValueError(f"{cell!r} is not a finite number")
    return value


def _key(row: dict) -> ContractKey:
    return ContractKey(date.fromisoformat(row["expiry"]), _finite(row["strike"]), OptionKind(row["type"]))


def _quote(row: dict) -> SlotQuote:
    return SlotQuote(_number(row["bid"]), _number(row["ask"]), _size(row["bid_qty"]), _size(row["ask_qty"]),
                     _number(row["last"]), row["valid"] == "true")  # fmt: skip


def _number(cell: str) -> float | None:
    return _finite(cell) if cell else None


def _size(cell: str) -> int | None:
    return round(_finite(cell)) if cell else None
