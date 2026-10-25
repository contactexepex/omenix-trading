"""The reader ports FL1 and the dashboard use (story section 3), over the verified Drive cache's local `data` folder
(the caller syncs it); they never build a path. Every chance carries its `measure` label, and every calibration
figure carries its number of expiries."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .chances import ContractChance, expiry_chances
from .folders import CALIBRATION
from .records import cached_records


class ItmChances:
    def __init__(self, data_root: Path, method_sha256: str):
        self.data_root, self.method_sha256 = data_root, method_sha256
        self._by_day: dict[tuple[str, date], list[ContractChance]] | None = None

    def for_day(self, underlying: str, day: date) -> list[ContractChance]:
        """Every monthly contract G13 valued that day, each source (3pm, backfill_eod) apart."""
        return list(self._index().get((underlying, day), []))

    def for_contract(self, underlying: str, day: date, expiry: date, strike: float, side: str,
                     source: str | None = None) -> ContractChance | None:  # fmt: skip
        """The contract's chance; with more than one source that day, `source` picks one (else the 3 pm chain)."""
        found = [c for c in self.for_day(underlying, day) if (c.expiry, c.strike, c.side) == (expiry, strike, side)
                 and (source is None or c.source == source)]  # fmt: skip
        return min(found, key=lambda c: c.source) if found else None  # "3pm" sorts before "backfill_eod"

    def _index(self) -> dict[tuple[str, date], list[ContractChance]]:
        if self._by_day is None:
            index = defaultdict(list)
            for record in cached_records(self.data_root, self.method_sha256):
                for e in expiry_chances(record):
                    index[(e.underlying, e.day)].extend(e.chances())
            self._by_day = dict(index)
        return self._by_day


@dataclass(frozen=True)
class CalibrationReport:
    underlying: str
    last_settled_expiry: str | None
    as_of: str
    measure: str
    notes: tuple[str, ...]
    settled_expiries: tuple[str, ...]
    left_out: tuple[dict, ...]
    slices: dict  # slice name -> {rows, expiries, buckets: [{bucket, brier, ..., expiries, bins: [...]}]}

    @classmethod
    def of(cls, data: dict) -> CalibrationReport:
        return cls(data["underlying"], data["last_settled_expiry"], data["as_of"], data["measure"],
                   tuple(data["notes"]), tuple(data["settled_expiries"]), tuple(data["left_out"]),
                   data["slices"])  # fmt: skip


class ItmCalibration:
    def __init__(self, data_root: Path):
        self.folder = data_root / CALIBRATION

    def latest(self, underlying: str) -> CalibrationReport | None:
        """The report with the latest settled expiry (then the latest `as_of`), or None before the first."""
        found = [json.loads(p.read_text(encoding="utf-8"))
                 for p in sorted(self.folder.glob(f"{underlying.lower()}_*.json"))]  # fmt: skip
        found = [d for d in found if d["underlying"] == underlying]
        if not found:
            return None
        return CalibrationReport.of(max(found, key=lambda d: (d["last_settled_expiry"] or "", d["as_of"])))
