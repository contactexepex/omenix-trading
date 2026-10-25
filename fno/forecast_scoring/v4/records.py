"""What a look writes and reads (story G8), and the freeze and slot registrations it depends on. Before protocol v4's
freeze record exists nothing is a look record: every output is exploratory. After it, each look's record is written
once (`look_<name>.json`) and never overwritten; look 2 reads look 1's to know which members closed."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ...constants import V4_CLAIM
from ...forecast_v4.terms import LOOK_STOP_REVIEW

EXPLORATORY = "EXPLORATORY: protocol v4 not frozen; nothing here counts"


FROZEN_ON = re.compile(r"^Frozen on: (\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)  # a line the freeze record carries


class FreezeDateMissing(RuntimeError):
    """The freeze record must state its day ("Frozen on: YYYY-MM-DD"): only live forecasts after it count."""


class LookRecordExists(RuntimeError):
    """A look's record is written once; a second write is refused."""


@dataclass(frozen=True)
class Registration:
    """A slot's registered forecaster and its declared `effective_start` (owner, 16 Oct 2026: misses count from it,
    even before the slot's first forecast; ChatGPT review 119)."""

    forecaster: str
    effective_start: date


class SlotRegistry(ABC):
    @abstractmethod
    def registered(self) -> dict[tuple[str, str], Registration]:
        """(question, slot) -> its registration, written in the ledger before the slot's first eligible session."""


class NoRegistrations(SlotRegistry):
    """Before the freeze writes its ledger row, no slot has a registered forecaster (Test A: undecided)."""

    def registered(self) -> dict[tuple[str, str], Registration]:
        return {}


class LookRecords:
    def __init__(self, folder: Path, freeze_file: Path):
        self.folder, self.freeze_file = Path(folder), Path(freeze_file)

    def frozen(self) -> bool:
        return self.freeze_file.is_file()

    def frozen_on(self) -> date:
        found = FROZEN_ON.search(self.freeze_file.read_text(encoding="utf-8"))
        if found is None:
            raise FreezeDateMissing(f"{self.freeze_file.name} has no 'Frozen on: YYYY-MM-DD' line")
        return date.fromisoformat(found.group(1))

    def path(self, look: str) -> Path:
        return self.folder / f"look_{look}.json"

    def write(self, look: str, payload: dict) -> Path:
        path = self.path(look)
        if path.exists():
            raise LookRecordExists(f"{path.name} is already written; a look is recorded once")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def closed(self, look: str) -> set[tuple[str, str]]:
        """Members closed at look 1 (a claim or a futility "no"), for look 2; none for look 1."""
        if look == LOOK_STOP_REVIEW or not self.path(LOOK_STOP_REVIEW).is_file():
            return set()
        members = json.loads(self.path(LOOK_STOP_REVIEW).read_text(encoding="utf-8"))["members"]
        return {(m["question"], m["slot"]) for m in members if m["verdict"] == V4_CLAIM or m["futile"]}
