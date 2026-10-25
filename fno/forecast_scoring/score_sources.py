"""Where story G4's forecasts come from.

- **History back-fill** (`research/forecasts/backfill/backfill_v1.csv.gz`): only rows dated on or after the scored
  window's first day. Earlier rows are dropped by their date text before any field is parsed (2019-2023 is experiment
  1's holdout; the orchestrator's rule for G4).
- **Live records** (`research/forecasts/live_v2/<YYYY>/<d>_pack.json` and `<d>_forecasts.csv`): scored only when both
  files hash to the day's capture receipt (protocol v2 section 5: the Git commit is transport, the receipt is the lock).
  `CaptureReceipts` is the interface; `RunSummaryReceipts` reads the receipt lines the capture saves in its run summary
  (Drive's pipeline area, `runs/forecast-capture/<YYYY>/<MM>/<run>.json`).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ..forecast.iv30 import AtmIv30
from ..forecast.record_files import read_records, read_records_v2
from ..storage.raw_store import RawFileStore
from .q5_thresholds import pack_iv30
from .score_inputs import ScoredForecast, from_backfill, from_live

RECEIPT = re.compile(r"receipt: (\d{4}-\d{2}-\d{2}) pack ([0-9a-f]{64}) records ([0-9a-f]{64})")
CAPTURE_RUNS = "runs/forecast-capture"
PACK_SUFFIX, RECORDS_SUFFIX = "_pack.json", "_forecasts.csv"


def backfill_forecasts(data: bytes, first_day: date) -> list[ScoredForecast]:
    """The back-fill's forecasts dated `first_day` or later; earlier lines are skipped unparsed (date is column 2)."""
    lines = gzip.decompress(data).decode("utf-8").splitlines(keepends=True)
    start = first_day.isoformat()
    kept = [lines[0]] + [line for line in lines[1:] if line.split(",", 2)[1] >= start]
    return [from_backfill(r) for r in read_records("".join(kept))]


@dataclass(frozen=True)
class Receipt:
    pack_sha256: str
    records_sha256: str


class CaptureReceipts(ABC):
    @abstractmethod
    def receipt(self, day: date) -> Receipt | None:
        """The capture's receipt for `day`, if one was saved."""


class RunSummaryReceipts(CaptureReceipts):
    def __init__(self, store: RawFileStore):
        self.store = store

    def receipt(self, day: date) -> Receipt | None:
        folder = f"{CAPTURE_RUNS}/{day:%Y}/{day:%m}"
        for name in sorted(self.store.checksums(folder)):  # file names directly in the month's folder
            data = self.store.get(f"{folder}/{name}")
            for note in json.loads(data or b"{}").get("notes", []):
                for found in RECEIPT.finditer(note):
                    if found.group(1) == day.isoformat():
                        return Receipt(found.group(2), found.group(3))
        return None


class NoReceipts(CaptureReceipts):
    """No receipt store reachable (no Drive credentials): every live day stays unverified, never scored."""

    def receipt(self, day: date) -> Receipt | None:
        return None


@dataclass
class LiveForecasts:
    forecasts: list[ScoredForecast] = field(default_factory=list)
    late: int = 0  # records generated after their deadline (not scored)
    unverified: list[str] = field(default_factory=list)  # days whose files do not match a receipt (not scored)
    packs: dict[date, str] = field(default_factory=dict)  # receipt-verified day -> its pack's SHA-256
    pack_iv30: dict[date, AtmIv30 | None] = field(default_factory=dict)  # verified day -> the pack's 15:00 IV30


def live_forecasts(folder: Path, receipts: CaptureReceipts) -> LiveForecasts:
    out = LiveForecasts()
    for records_path in sorted(folder.glob(f"*/*{RECORDS_SUFFIX}")):
        day = date.fromisoformat(records_path.name.removesuffix(RECORDS_SUFFIX))
        pack_path = records_path.with_name(f"{day.isoformat()}{PACK_SUFFIX}")
        receipt, text = receipts.receipt(day), records_path.read_text(encoding="utf-8")
        pack = pack_path.read_bytes() if pack_path.is_file() else None
        if receipt is None or pack is None or receipt != Receipt(_sha256(pack), _sha256(text.encode("utf-8"))):
            out.unverified.append(day.isoformat())
            continue
        out.packs[day], out.pack_iv30[day] = receipt.pack_sha256, pack_iv30(pack)
        for record in read_records_v2(text):
            scored = from_live(record)
            if scored is None:
                out.late += 1
            else:
                out.forecasts.append(scored)
    return out


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
