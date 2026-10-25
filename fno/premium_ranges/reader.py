"""G13d's files read back from the verified Drive cache's local `data` folder (the caller syncs it): the issued
records, G13's record of the next session, the stored seals and the latest scores report. FL1 and the dashboard use
`PremiumRanges` and `PremiumScores`; they never build a path."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..price_distribution.folders import live_path as g13_live_path
from .constants import ISSUE, RULE
from .folders import LIVE, SCORES, live_path, seal_path


def _json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def issued_records(data_root: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((data_root / LIVE).rglob("*.json"))]


def g13_record(data_root: Path, underlying: str, day: date) -> dict | None:
    return _json(data_root / g13_live_path(underlying, day))


def stored_seal(data_root: Path, underlying: str, day: date) -> dict | None:
    return _json(data_root / seal_path(underlying, day, ISSUE))


@dataclass(frozen=True)
class PremiumRange:
    underlying: str
    day: date
    next_session: date
    expiry: date
    strike: float
    side: str
    mid: float  # d's 3 pm mid
    quantiles: tuple[float, ...]  # the rule's 5/25/50/75/95% premium at d+'s 3 pm, rupees
    sealed_at: str | None  # GitHub's push time of the receipt, once the seal is stored
    late: bool | None  # None while the seal is not yet stored
    rule: str = RULE


class PremiumRanges:
    def __init__(self, data_root: Path):
        self.data_root = data_root

    def for_day(self, underlying: str, day: date) -> list[PremiumRange]:
        record = _json(self.data_root / live_path(underlying, day, ISSUE))
        if record is None:
            return []
        seal = stored_seal(self.data_root, underlying, day) or {}
        return [PremiumRange(underlying, day, date.fromisoformat(record["next_session"]),
                             date.fromisoformat(r["expiry"]), r["strike"], r["side"], r["mid"], tuple(r[RULE]),
                             seal.get("sealed_at"), seal.get("late")) for r in record["rows"]]  # fmt: skip


class PremiumScores:
    def __init__(self, data_root: Path):
        self.folder = data_root / SCORES

    def latest(self, underlying: str) -> dict | None:
        """The underlying's part of the latest scores report (sessions, looks, buckets), or None before the first."""
        reports = sorted(self.folder.glob("*.json"))
        if not reports:
            return None
        return json.loads(reports[-1].read_text(encoding="utf-8"))["underlyings"].get(underlying)
