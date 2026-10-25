"""Status changes of a strategy version (story D1 criterion 3): check the change, append its registry row, then set
the file's `status` line to match. The row is checked with the same approval checks the loader runs, before anything
is written. Commit the registry and the file together; the evidence for a change to paper must already be committed
(its commit is recorded in the row, by default the current HEAD)."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date

from ..constants import PlaybookStatus
from .fields import PlaybookError
from .history import History
from .loader import PlaybookLoader
from .registry import RegistryRow
from .transitions import PAPER, check_transition

STATUS_LINE = re.compile(r"^status:[ \t]*\S+[ \t]*$", re.MULTILINE)


class StatusChanger:
    def __init__(self, loader: PlaybookLoader, history: History):
        self.loader, self.history = loader, history

    def change(
        self, name: str, version: int, status: PlaybookStatus, approved_by: str, on: date, evidence_commit: str = ""
    ) -> RegistryRow:
        """Appends the change and updates the file; PlaybookError (nothing written) if it is not allowed. Every check
        (git reads included) runs before the first write: the whole playbook loads, and this version passes the
        loader's checks with its new row, so the two writes leave nothing to check after them."""
        strategy = self.loader.load().get(name, version)
        history = [row for row in self.loader.registry.rows() if row.key == strategy.key]
        check_transition(history[-1].status if history else None, status, approved_by)
        if status == PAPER and not evidence_commit:
            evidence_commit = self.history.head()
        row = RegistryRow(name, version, strategy.parameters_sha256, status, on, approved_by, evidence_commit)
        self.loader.check_against_history(replace(strategy, status=status), [*history, row])
        path = self.loader.folder / strategy.file_name
        text = path.read_text(encoding="utf-8")
        if len(STATUS_LINE.findall(text)) != 1:
            raise PlaybookError(f"{strategy.file_name}: status", "needs exactly one top-level `status:` line")
        self.loader.registry.append(row)
        path.write_text(STATUS_LINE.sub(f"status: {status}", text), encoding="utf-8")
        return row
