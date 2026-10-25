"""The live forecast input pack of protocol version 2 (story G1 v2; ChatGPT review 29, response 63).

Built from the day's canonical A4 snapshot (raw CSV and meta bytes), the official closes before the day and the
session calendar, for the 15:00:00 IST cutoff. Rules (PROTOCOL_v2.md):
1. **Per-field cutoff:** a same-day field enters only if its own time is at or before 15:00:00 IST. Option quotes and
   spot: the row's `response_received_at`. Futures: they carry no time of their own; A4 reads them inside the capture
   before the first quote request, so that request's `request_sent_at` bounds their retrieval. India VIX: NSE's own
   timestamp (`india_vix_time`) and the same retrieval bound. A field without a trustworthy time at or before 15:00
   is missing.
2. **IV30 from live mids:** B7's live ATM rule (strike nearest the 15:00 spot, a tie to the lower; both legs valid and
   two-sided, mid = (bid + ask) / 2; Black-76 on the same-expiry future), then G1's `interpolate_30d` unchanged:
   monthly expiries are the futures listed that day; a bracketing expiry A4 did not capture has no IV, so the
   protocol's fallback and flag apply.
3. **Provenance in the hash:** the pack lists every value it supplies with its source and time, the snapshot id and
   file hashes, the closes' source, coverage date and table hash, and the calendar hash. Its canonical JSON is hashed.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import date, datetime, time

from ..models import IST
from ..research_data.panel_reader import FutureQuote
from ..research_data.quote_snapshots import CutoffSnapshot, LiveQuote
from ..research_engine.live_features import LiveAtmIvMinusRealised
from .iv30 import AtmIv30, interpolate_30d

CUTOFF = time(15, 0, 0)
LIVE_MODE = "live_1500_proxy"
NSE_TIME_FORMATS = ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M")


@dataclass(frozen=True)
class PackField:
    name: str
    value: float | str | None
    source: str
    observed_at: str  # ISO time in IST of the observation; "" for a value derived from observed fields


@dataclass
class LivePack:
    day: date
    snapshot: dict[str, str]
    closes: dict[str, str]
    calendar_sha256: str
    fields: list[PackField] = field(default_factory=list)
    iv30: AtmIv30 | None = None
    problems: list[str] = field(default_factory=list)

    def value(self, name: str) -> float | None:
        found = next((f for f in self.fields if f.name == name), None)
        return found.value if found is not None and isinstance(found.value, float) else None

    @property
    def iv30_status(self) -> str:
        return "none" if self.iv30 is None else "flagged" if self.iv30.flagged else "interpolated"

    def canonical(self) -> bytes:
        body = {
            "day": self.day.isoformat(), "cutoff": f"{self.day.isoformat()}T15:00:00+05:30", "mode": LIVE_MODE,
            "snapshot": self.snapshot, "closes": self.closes, "calendar_sha256": self.calendar_sha256,
            "fields": [vars(f) for f in self.fields], "problems": sorted(self.problems),
            "iv30": None if self.iv30 is None else {"points": self.iv30.points, "status": self.iv30_status,
                                                    "expiries": [e.isoformat() for e in self.iv30.expiries]},
        }  # fmt: skip
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical()).hexdigest()


def _aware(text: str) -> datetime | None:
    if not text:
        return None
    moment = datetime.fromisoformat(text)
    return (moment if moment.tzinfo else moment.replace(tzinfo=IST)).astimezone(IST)


def _nse_time(text: str) -> datetime | None:
    for fmt in NSE_TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=IST)
        except ValueError:
            continue
    return None


def _observed_by(text: str, cutoff: datetime) -> bool:
    moment = _aware(text)
    return moment is not None and moment <= cutoff


def _number(text: str) -> float | None:
    return float(text) if text else None


@dataclass(frozen=True)
class SnapshotFiles:
    snapshot_id: str
    dataset: str
    csv_bytes: bytes
    meta_bytes: bytes


class LivePackBuilder:
    def __init__(self, iv_rule: LiveAtmIvMinusRealised):
        self.iv_rule = iv_rule  # B7's live ATM implied volatility (model, rate)

    def build(self, day: date, files: SnapshotFiles, closes: dict[str, str], calendar_sha256: str) -> LivePack:
        cutoff = datetime.combine(day, CUTOFF, tzinfo=IST)
        pack = LivePack(day, _snapshot_ids(files), closes, calendar_sha256)
        rows = list(csv.DictReader(io.StringIO(files.csv_bytes.decode("utf-8"))))
        meta = json.loads(files.meta_bytes)
        quotes = [r for r in rows if _observed_by(r["response_received_at"], cutoff)]
        spot = self._spot(pack, quotes)
        bound = min((_aware(r["request_sent_at"]) for r in rows), default=_aware(meta.get("finished_at", "")))
        self._vix(pack, meta, bound, cutoff)
        futures = self._futures(pack, meta, bound, cutoff)
        if spot is not None:
            pack.iv30 = self._iv30(pack, day, spot, quotes, futures)
        return pack

    @staticmethod
    def _spot(pack: LivePack, quotes: list[dict]) -> float | None:
        latest = max(quotes, key=lambda r: _aware(r["response_received_at"]), default=None)
        if latest is None or not latest["spot"]:
            pack.problems.append("no NIFTY spot observed by 15:00")
            return None
        pack.fields.append(
            PackField("nifty_spot", float(latest["spot"]), "a4 quote row", latest["response_received_at"])
        )
        return float(latest["spot"])

    @staticmethod
    def _vix(pack: LivePack, meta: dict, bound: datetime | None, cutoff: datetime) -> None:
        stamp, value = _nse_time(str(meta.get("india_vix_time", ""))), meta.get("india_vix")
        if value is None or stamp is None or stamp > cutoff or bound is None or bound > cutoff:
            pack.problems.append("no India VIX observed by 15:00")
            return
        pack.fields.append(PackField("india_vix", float(value), "a4 meta india_vix (NSE timestamp)", stamp.isoformat()))

    @staticmethod
    def _futures(pack: LivePack, meta: dict, bound: datetime | None, cutoff: datetime) -> tuple[FutureQuote, ...]:
        if bound is None or bound > cutoff:
            pack.problems.append("no NIFTY futures observed by 15:00")
            return ()
        futures = []
        for f in meta.get("futures", []):
            expiry = date.fromisoformat(f["expiry"])
            pack.fields.append(PackField(f"future_{expiry.isoformat()}", float(f["last"]), "a4 meta futures (last)",
                                         bound.isoformat()))  # fmt: skip
            pack.fields.append(PackField(f"future_{expiry.isoformat()}_volume", str(f["volume"]), "a4 meta futures",
                                         bound.isoformat()))  # fmt: skip
            futures.append(FutureQuote(expiry, float(f["last"]), 0.0, int(f["volume"]), 0))
        return tuple(futures)

    def _iv30(self, pack, day, spot, quotes, futures) -> AtmIv30 | None:
        live = tuple(
            LiveQuote(
                date.fromisoformat(r["expiry"]),
                float(r["strike"]),
                r["type"],
                _number(r["bid"]),
                _number(r["ask"]),
                r["valid"] == "true",
            )  # fmt: skip
            for r in quotes
        )
        snapshot = CutoffSnapshot(day, datetime.combine(day, CUTOFF), spot, None, live, futures)
        monthly = sorted(f.expiry for f in futures if f.expiry >= day)
        ivs = {e: self.iv_rule.atm_implied_vol_points(snapshot, e) for e in monthly}
        for expiry, iv in ivs.items():
            pack.fields.append(
                PackField(f"atm_iv_{expiry.isoformat()}", iv, "derived: B7 live ATM rule on a4 mids", "")
            )
        return interpolate_30d(day, ivs)


def _snapshot_ids(files: SnapshotFiles) -> dict[str, str]:
    return {
        "dataset": files.dataset,
        "snapshot_id": files.snapshot_id,
        "csv_sha256": hashlib.sha256(files.csv_bytes).hexdigest(),
        "meta_sha256": hashlib.sha256(files.meta_bytes).hexdigest(),
    }
