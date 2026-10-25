"""A captured row (response 327 P0b): instrument, contract, expiry, dated lot, source time, first-seen time, the raw
answer's SHA-256 and a quality status. A row keeps no price: the prices stay in the raw answer, in Drive."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime

from .constants import STALE_AFTER, Quality, RowKind

FLAG_JOIN = "+"


@dataclass(frozen=True)
class CaptureRow:
    kind: RowKind
    instrument: str
    contract: str
    expiry: str
    lot: int | None
    source_time: str | None
    first_seen: str
    raw_sha256: str
    quality: str

    def as_line(self) -> dict:
        return {"row": asdict(self)}


def quality_of(bid: float | None, ask: float | None, lot: int | None, source_time: datetime | None,
               first_seen: datetime) -> str:  # fmt: skip
    """Every flag that applies, joined by "+" ("ok" when none): one row can be one-sided and of unknown lot at once,
    and the empty bid/ask share must count it either way."""
    flags = []
    if not bid and not ask:
        flags.append(Quality.EMPTY_BID_ASK)
    elif not bid or not ask:
        flags.append(Quality.ONE_SIDED)
    if source_time is not None and first_seen - source_time > STALE_AFTER:
        flags.append(Quality.STALE)
    if lot is None:
        flags.append(Quality.LOT_UNKNOWN)
    return FLAG_JOIN.join(flags) if flags else Quality.OK


def captured(kind: RowKind, instrument: str, contract: str, expiry: date, lot: int | None,
             bid: float | None, ask: float | None, source_time: datetime | None, first_seen: datetime,
             raw_sha256: str) -> CaptureRow:  # fmt: skip
    return CaptureRow(kind, instrument, contract, expiry.isoformat(), lot,
                      source_time.isoformat() if source_time else None, first_seen.isoformat(), raw_sha256,
                      quality_of(bid, ask, lot, source_time, first_seen))  # fmt: skip


def missing(kind: RowKind, instrument: str, contract: str, expiry: date | None, first_seen: datetime) -> CaptureRow:
    return CaptureRow(kind, instrument, contract, expiry.isoformat() if expiry else "", None, None,
                      first_seen.isoformat(), "", Quality.MISSING)  # fmt: skip


def flags_of(row: CaptureRow) -> list[str]:
    return row.quality.split(FLAG_JOIN)
