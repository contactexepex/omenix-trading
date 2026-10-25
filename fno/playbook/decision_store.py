"""Where decision records live (story D3): `journal/<book>/decisions/<date>/<run_id>/`, one folder per run holding the
run's replay inputs (`inputs.json`), one record per opportunity and mode (a shadow's is `shadow_<id>.json`, story R3)
and `records.sha256` (`sha256sum -c` form).

- **Atomic:** the whole run is written into a hidden temporary folder and renamed into place, so a crash leaves the
  complete run or nothing (criterion 3). Hidden folders are never read as runs.
- **Written once:** an existing run is never written again; a correction is a new run whose record names the one it
  corrects (criterion 4). `edited` finds any file changed after writing.
- **Idempotent:** a run whose inputs equal an earlier run's of the same day is refused."""

from __future__ import annotations

import hashlib
import os
import shutil
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from ..constants import JOURNAL_FOLDER
from ..desk.pack_items import canonical_json
from .decision_record import validate_record
from .opportunities import SHADOW

DECISIONS_FOLDER, INPUTS_FILE, SUMS_FILE = "decisions", "inputs.json", "records.sha256"


class DuplicateRun(ValueError):
    """The same inputs were already decided today."""


class RecordClash(ValueError):
    """Two records of one run would share a file: refused, never one silently kept."""


def record_file(opportunity_id: str, mode: str | None = None) -> str:
    """A shadow record's name carries its mode (story R3), so a book's and a shadow's record of the same opportunity
    both survive; a version name is `[a-z0-9-]` only, so the `shadow_` prefix never matches a book record's name."""
    return (f"{SHADOW}_" if mode == SHADOW else "") + opportunity_id.replace(":", "_") + ".json"


class DecisionStore:
    def __init__(self, root: Path, book: str):
        self.folder = Path(root) / JOURNAL_FOLDER / book / DECISIONS_FOLDER

    def day_folder(self, day: date) -> Path:
        return self.folder / day.isoformat()

    def runs(self, day: date) -> list[Path]:
        folder = self.day_folder(day)
        return (
            sorted(p for p in folder.iterdir() if p.is_dir() and not p.name.startswith(".")) if folder.is_dir() else []
        )

    def every_run(self) -> list[Path]:
        """Every run of the book, hidden temporary folders aside, in no meaningful order: for readers that need all of
        them, never "the first" (that is `run_order.ordered_runs`)."""
        days = (
            sorted(p for p in self.folder.iterdir() if p.is_dir() and not p.name.startswith("."))
            if self.folder.is_dir()
            else []
        )
        return [run for day in days for run in self.runs(date.fromisoformat(day.name))]

    def next_run_id(self, day: date) -> str:
        return f"{day.isoformat()}-r{len(self.runs(day)) + 1}"

    def write(self, day: date, run_id: str, inputs: bytes | None, records: Sequence[dict]) -> Path:
        for record in records:
            validate_record(record)
        target = self.day_folder(day) / run_id
        if target.exists():
            raise FileExistsError(f"{target} exists: decision records are never rewritten")
        if inputs is not None:
            self._refuse_duplicate(day, inputs)
        files = self._record_files(records)
        if inputs is not None:
            files[INPUTS_FILE] = inputs
        temporary = target.with_name(f".{run_id}.tmp")
        shutil.rmtree(temporary, ignore_errors=True)  # a crashed earlier attempt's leftovers
        temporary.mkdir(parents=True)
        for name, data in sorted(files.items()):
            (temporary / name).write_bytes(data)
        sums = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(files.items()))
        (temporary / SUMS_FILE).write_text(sums, encoding="utf-8")
        os.rename(temporary, target)
        return target

    @staticmethod
    def _record_files(records: Sequence[dict]) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        for record in records:
            name = record_file(record["opportunity_id"], record.get("mode"))
            if name in files:
                raise RecordClash(f"two records of this run would both be {name}: refused, nothing written")
            files[name] = canonical_json(record)
        return files

    def _refuse_duplicate(self, day: date, inputs: bytes) -> None:
        for run in self.runs(day):
            earlier = run / INPUTS_FILE
            if earlier.is_file() and earlier.read_bytes() == inputs:
                raise DuplicateRun(f"{run.name} already decided these inputs for {day}: refused")

    @staticmethod
    def edited(run: Path) -> list[str]:
        """The files of a run that differ from (or are missing against) its `records.sha256`."""
        problems = []
        for line in (run / SUMS_FILE).read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            path = run / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                problems.append(name)
        return problems
