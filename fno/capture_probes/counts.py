"""The day's counts file (story MS-P0b section 5): requests, refusals, row qualities, latency and Drive writes per
slot and source; counts and times only, never a price. It also carries the cap's reservations (judge 626): a slot's
whole budget is written as reserved before its first request and replaced by the real count at its end, so a run that
dies mid-slot leaves its calls counted in full."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from .constants import Source


@dataclass
class SourceSlot:
    reserved: int
    used: int | None = None  # None until the slot ended: the reservation counts in full
    refusals: dict[str, int] = field(default_factory=dict)
    quality: dict[str, int] = field(default_factory=dict)
    rows: int = 0
    latency_ms: dict[str, float] = field(default_factory=dict)
    drive: str = "none"
    stop: str = ""

    def spent(self) -> int:
        return self.reserved if self.used is None else self.used


@dataclass
class DayCounts:
    session: str
    slots: dict[str, dict[str, SourceSlot]] = field(default_factory=dict)
    stops: dict[str, str] = field(default_factory=dict)

    def spent(self, source: Source) -> int:
        return sum(entry[source].spent() for entry in self.slots.values() if source in entry)

    def started(self) -> bool:
        return bool(self.slots)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=1, sort_keys=True) + "\n"

    @classmethod
    def from_json(cls, text: str) -> DayCounts:
        raw = json.loads(text)
        slots = {name: {source: SourceSlot(**entry) for source, entry in by_source.items()}
                 for name, by_source in raw.get("slots", {}).items()}  # fmt: skip
        return cls(raw["session"], slots, dict(raw.get("stops", {})))


class CountsFolder:
    """One JSON file per session, `<folder>/<session>.json`."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def path_for(self, session: date) -> Path:
        return self.folder / f"{session.isoformat()}.json"

    def read(self, session: date) -> DayCounts:
        path = self.path_for(session)
        return DayCounts.from_json(path.read_text(encoding="utf-8")) if path.is_file() else DayCounts(str(session))

    def write(self, counts: DayCounts) -> None:
        path = self.path_for(date.fromisoformat(counts.session))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(counts.to_json(), encoding="utf-8")

    def earlier(self, session: date) -> list[DayCounts]:
        """Every other session's counts, oldest first."""
        files = sorted(p for p in self.folder.glob("*.json") if p.stem != session.isoformat())
        return [DayCounts.from_json(p.read_text(encoding="utf-8")) for p in files]
