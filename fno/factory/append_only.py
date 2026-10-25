"""One append-only CSV file of the factory (story R1): the gate log and the research questions.

Rows are only ever appended; an edit or deletion of an earlier row, in the working file or anywhere in its git history,
is refused (D1's append-only check)."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Protocol

from ..playbook.registry import rewritten_history


class FileHistory(Protocol):
    def file_versions(self, path: str) -> list[str]: ...


def _render(*lines: tuple) -> str:
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(lines)
    return out.getvalue()


class AppendOnlyCsv:
    def __init__(self, root: Path, path: str, columns: tuple[str, ...], history: FileHistory, error: type[ValueError]):
        self.file, self.path, self.columns = Path(root) / path, path, columns
        self.history, self.error = history, error

    def _text(self) -> str:
        return self.file.read_text(encoding="utf-8") if self.file.is_file() else ""

    def lines(self) -> list[list[str]]:
        reader = csv.reader(io.StringIO(self._text()))
        header = next(reader, None)
        if header is not None and tuple(header) != self.columns:
            raise self.error(f"{self.path} columns must be {self.columns}")
        return [line for line in reader if line]

    def history_problems(self) -> list[str]:
        """Earlier rows edited or deleted, in git history or in the working file (empty when append-only)."""
        current = [self._text()] if self.file.is_file() else []
        return rewritten_history(self.history.file_versions(self.path) + current)

    def require_append_only(self) -> None:
        problems = self.history_problems()
        if problems:
            raise self.error(f"{self.path} history is not append-only: {'; '.join(problems)}")

    def append(self, values: tuple) -> None:
        self.prepare(values)()

    def prepare(self, values: tuple) -> Callable[[], None]:
        """Checks the history now (git reads) and returns the write, which reads nothing: a caller with other writes
        checks every file first, so a failed git read leaves nothing half written."""
        self.require_append_only()
        return partial(self._write, values)

    def _write(self, values: tuple) -> None:
        before = self._text() or _render(self.columns)
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(before + _render(values), encoding="utf-8")
