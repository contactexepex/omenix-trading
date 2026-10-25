"""The append-only playbook registry `playbook/registry.csv` (story D1 criteria 2-3): one row per registration or
status change of a strategy version, with the version's parameter fingerprint. The latest row of a version decides its
status; every row of a version carries the same fingerprint, so a changed parameter can never join an existing
version. Past rows are never edited: `rewritten_history` checks the committed history of the file."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from ..constants import PlaybookStatus
from .fields import PlaybookError
from .schema import COMMIT_PATTERN
from .transitions import PAPER, check_transition

COLUMNS = ("name", "version", "sha256", "status", "changed_on", "approved_by", "evidence_commit")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class RegistryRow:
    name: str
    version: int
    sha256: str
    status: PlaybookStatus
    changed_on: date
    approved_by: str
    evidence_commit: str  # the commit holding the evidence the change rests on; required for a change to paper

    @property
    def key(self) -> tuple[str, int]:
        return self.name, self.version

    def as_csv(self) -> dict:
        return {**asdict(self), "status": str(self.status), "changed_on": self.changed_on.isoformat()}


def parse_rows(text: str) -> list[RegistryRow]:
    """Every row, after checking columns, values and that each version's rows form an allowed history."""
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise PlaybookError("registry.csv", f"columns must be {COLUMNS}")
    rows = [_row(raw, line) for line, raw in enumerate(reader, start=2)]
    _check_histories(rows)
    return rows


def _row(raw: dict, line: int) -> RegistryRow:
    where = f"registry.csv line {line}"
    try:
        row = RegistryRow(
            raw["name"], int(raw["version"]), raw["sha256"], PlaybookStatus(raw["status"]),
            date.fromisoformat(raw["changed_on"]), raw["approved_by"], raw["evidence_commit"],
        )  # fmt: skip
    except (TypeError, ValueError) as bad:
        raise PlaybookError(where, f"unreadable row: {bad}") from None
    if not SHA256_PATTERN.fullmatch(row.sha256):
        raise PlaybookError(f"{where} sha256", "must be 64 lower-case hex characters")
    if row.evidence_commit and not COMMIT_PATTERN.fullmatch(row.evidence_commit):
        raise PlaybookError(f"{where} evidence_commit", "must be a git commit id")
    if row.status == PAPER and not row.evidence_commit:
        raise PlaybookError(f"{where} evidence_commit", "a change to paper must name the commit of its evidence")
    return row


def _check_histories(rows: Sequence[RegistryRow]) -> None:
    previous: dict[tuple[str, int], RegistryRow] = {}
    for row in rows:
        before = previous.get(row.key)
        where = f"registry.csv {row.name} v{row.version}"
        try:
            check_transition(before.status if before else None, row.status, row.approved_by)
        except PlaybookError as refused:
            raise PlaybookError(f"{where} {refused.field}", refused.reason) from None
        if before and row.sha256 != before.sha256:
            raise PlaybookError(
                f"{where} sha256", "differs from the version's earlier rows: a changed rule is a new version"
            )
        if before and row.changed_on < before.changed_on:
            raise PlaybookError(f"{where} changed_on", "is before the version's previous change")
        previous[row.key] = row


def render(rows: Sequence[RegistryRow]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(row.as_csv() for row in rows)
    return out.getvalue()


class Registry:
    """The registry file: read, latest row per version, and append (never rewrite)."""

    def __init__(self, path: Path):
        self.path = path

    def rows(self) -> list[RegistryRow]:
        return parse_rows(self.path.read_text(encoding="utf-8")) if self.path.is_file() else []

    def latest(self) -> dict[tuple[str, int], RegistryRow]:
        return {row.key: row for row in self.rows()}

    def append(self, row: RegistryRow) -> None:
        """Adds one row after checking the whole history with it; the existing bytes are kept as they are."""
        rows = [*self.rows(), row]
        parse_rows(render(rows))
        old = self.path.read_text(encoding="utf-8") if self.path.is_file() else render([])
        old += "" if old.endswith("\n") else "\n"
        line = render([row]).split("\n", 1)[1]
        self.path.write_text(old + line, encoding="utf-8")


def rewritten_history(versions: Sequence[str]) -> list[str]:
    """The problems in a registry's successive committed texts (oldest first): each text must start with the whole
    previous text (rows only ever appended). Empty when the history is append-only."""
    return [
        f"version {n + 1} does not keep version {n}'s rows unchanged"
        for n, (older, newer) in enumerate(zip(versions, versions[1:]))
        if not newer.startswith(older)
    ]
