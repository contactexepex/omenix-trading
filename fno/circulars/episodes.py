"""The problems already alerted (story A20b, judge 353 minor 1): one key per line in a committed text file (the
pattern of O8b's `calendar_horizon_alerted.txt`). Keys hold no value, URL or log text."""

from __future__ import annotations

from pathlib import Path


class OpenProblems:
    def __init__(self, file: Path):
        self.file = Path(file)

    def read(self) -> set[str]:
        if not self.file.is_file():
            return set()
        return {line.strip() for line in self.file.read_text(encoding="utf-8").splitlines() if line.strip()}

    def write(self, keys: set[str]) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text("".join(f"{key}\n" for key in sorted(keys)), encoding="utf-8")
