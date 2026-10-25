"""The weekly post-mortem's code-built lines (story LR1): the sections joined under one header, with G8's EXPLORATORY
line first before protocol v4's freeze; and its records in `research/postmortems/<YYYY>/`, each written once (the same
bytes again change nothing; different bytes for a week already written are refused)."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..forecast_scoring.v4.records import EXPLORATORY
from .week import Week

HEADER = "Omenix F&O weekly post-mortem, week ending {saturday} (PAPER ONLY: it reports and decides no trade)"
WRITTEN, ALREADY = "written", "already written"


class PostMortemSection(ABC):
    name: str

    @abstractmethod
    def lines(self, week: Week) -> list[str]: ...

    @abstractmethod
    def data(self, week: Week) -> dict: ...


@dataclass(frozen=True)
class Report:
    text: str
    data: dict


class PostMortemBuilder:
    def __init__(self, sections: Sequence[PostMortemSection], frozen: Callable[[], bool]):
        self.sections, self.frozen = sections, frozen

    def build(self, week: Week) -> Report:
        exploratory = not self.frozen()
        lines = [*([EXPLORATORY] if exploratory else []), HEADER.format(saturday=week.saturday)]
        for section in self.sections:
            lines += ["", *section.lines(week)]
        data = {"week_ending": week.saturday.isoformat(), "sessions": [d.isoformat() for d in week.sessions],
                "exploratory": exploratory, **{s.name: s.data(week) for s in self.sections}}  # fmt: skip
        return Report("\n".join(lines) + "\n", data)


class PostMortemConflict(RuntimeError):
    """A different post-mortem for this week is already written; nothing was changed."""


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PostMortemRecords:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def path(self, saturday: date, suffix: str = ".md") -> Path:
        return self.folder / f"{saturday:%Y}" / f"{saturday.isoformat()}{suffix}"

    def write(self, saturday: date, report: Report) -> str:
        files = {".md": report.text.encode(), ".json": (json.dumps(report.data, indent=1, sort_keys=True,
                 default=str) + "\n").encode()}  # fmt: skip
        if all(self.path(saturday, s).is_file() for s in files):
            if any(self.path(saturday, s).read_bytes() != b for s, b in files.items()):
                raise PostMortemConflict(f"post-mortem {saturday}: a different report is already written")
            return ALREADY
        for suffix, data in files.items():
            self.path(saturday, suffix).parent.mkdir(parents=True, exist_ok=True)
            self.path(saturday, suffix).write_bytes(data)
        return WRITTEN

    def read_json(self, saturday: date, suffix: str) -> dict | None:
        path = self.path(saturday, suffix)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def write_json_once(self, saturday: date, suffix: str, data: dict) -> None:
        path = self.path(saturday, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as out:  # "x": a fire log or publish record is never rewritten
            out.write(json.dumps(data, indent=1, sort_keys=True) + "\n")
