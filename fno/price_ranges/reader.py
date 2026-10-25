"""The reader port FL1 uses (part A8): sealed live ranges, back-fill records and the latest scores, all from the
verified Drive cache's local copy; FL1 never builds a path. A live record carries its seal (`sealed_at` from
GitHub's push time) and `late` when it is not sealed by its deadline."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .backfill import SCHEMA as BACKFILL_SCHEMA
from .constants import LIVE as LIVE_LABEL
from .folders import BACKFILL, LIVE, RECEIPTS_ROOT, SCORES, drive, live_path
from .sealing import Seal
from .seals import Seals


@dataclass(frozen=True)
class SealedRanges:
    record: dict
    seal: Seal

    @property
    def sealed_at(self):
        return self.seal.sealed_at

    @property
    def late(self) -> bool:
        return self.seal.late


def receipt_file(path: str) -> str:
    """The repository path of a G13b Drive file's receipt (O9: `receipts/<drive path>.sha256`)."""
    return f"{RECEIPTS_ROOT}/{drive(path)}.sha256"


class RangeForecasts:
    def __init__(self, cache_root: Path, seals: Seals):
        """`cache_root`: the Drive cache's local root (its files under `data/...`), synced by the caller; `seals`: the
        stored seal of a record, else one computed now (review finding 1)."""
        self.root, self.seals = Path(cache_root), seals

    def _read(self, path: str) -> dict | None:
        file = self.root / drive(path)
        return json.loads(file.read_bytes()) if file.is_file() else None

    def sealed(self, underlying: str, day: date, issue: str) -> SealedRanges | None:
        path = live_path(underlying, day, issue)
        record = self._read(path)
        return None if record is None else SealedRanges(record, self.seals.seal(underlying, day, issue))

    def live(self) -> Iterator[SealedRanges]:
        for file in sorted((self.root / drive(LIVE)).rglob("*.json")):
            record = json.loads(file.read_bytes())
            day = date.fromisoformat(record["day"])
            yield SealedRanges(record, self.seals.seal(record["underlying"], day, record["issue"]))

    def backfill(self) -> Iterator[dict]:
        """One record per (label, method, underlying, day, issue): overlapping or rerun back-fills never count twice;
        the file whose range ends latest (then its path) wins (review finding 4)."""
        documents = []
        for file in sorted((self.root / drive(BACKFILL)).rglob("*.json.gz")):
            document = json.loads(gzip.decompress(file.read_bytes()))
            if document.get("schema") == BACKFILL_SCHEMA:
                documents.append(((document["last"], file.as_posix()), document))
        chosen = {}
        for _, document in sorted(documents, key=lambda pair: pair[0]):
            for record in document["records"]:
                key = (record["label"], record["method_sha256"], record["underlying"], record["day"], record["issue"])
                chosen[key] = record
        yield from (chosen[key] for key in sorted(chosen))


class RangeScores:
    def __init__(self, cache_root: Path):
        self.root = Path(cache_root)

    def latest(self) -> dict | None:
        files = sorted((self.root / drive(SCORES)).glob("*.json"))
        return json.loads(files[-1].read_bytes()) if files else None

    def rows(self, underlying: str, live_only: bool = False) -> list[dict]:
        """The latest report's per-row scores of an underlying (live ones only when asked: FL1's history)."""
        report = self.latest() or {}
        return [r for r in report.get("rows", []) if r["underlying"] == underlying and (r["label"] == LIVE_LABEL or
                                                                                      not live_only)]  # fmt: skip

    def scored_days(self, underlying: str, through: date) -> list[date]:
        """The target days with at least one live score, up to `through` (FL1's trust line)."""
        days = {date.fromisoformat(r["target_day"]) for r in self.rows(underlying, live_only=True)}
        return sorted(d for d in days if d <= through)
