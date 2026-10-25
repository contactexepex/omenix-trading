"""The books' version registry `journal/versions.csv` (story D6, design 12.6 and 13.5): one append-only row per
version of a book (its playbook hashes, envelope, constitution, model, prompts, role set, source contract), with the
day it starts and the commit its components were frozen in (`registered_in_commit`, HEAD when it was registered).
The commit that holds the row itself is read from git, never trusted from the file: a version counts for a decision
only if that commit is an ancestor of the decision's commit, so no version is declared after seeing its decisions."""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..constants import BOOKS

SCHOOL_BOOK_PREFIX = "school:"  # a market school driver version's book: `school:<driver code>@<version>` (story MS-P1h)
SCHOOL_BOOK = re.compile(rf"{SCHOOL_BOOK_PREFIX}[A-Z][A-Z0-9]*@[1-9][0-9]*")
COLUMNS = ("book", "version_id", "starts_on", "registered_in_commit", "components", "reason")
FULL_COMMIT = re.compile(r"[0-9a-f]{40}")


def is_known_book(book: str) -> bool:
    """One of the three books, or a school driver version's id."""
    return book in BOOKS or SCHOOL_BOOK.fullmatch(book) is not None


class VersionError(ValueError):
    """A version row, or the registry, that may not be used; the message names the row."""


@dataclass(frozen=True)
class VersionRow:
    book: str
    version_id: str
    starts_on: date
    registered_in_commit: str
    components: Mapping[str, str]  # e.g. model, prompt versions, role set, playbook or constitution hashes
    reason: str

    def as_csv(self) -> dict:
        return {
            "book": self.book, "version_id": self.version_id, "starts_on": self.starts_on.isoformat(),
            "registered_in_commit": self.registered_in_commit,
            "components": json.dumps(dict(self.components), sort_keys=True, separators=(",", ":")),
            "reason": self.reason,
        }  # fmt: skip


def parse_versions(text: str) -> list[VersionRow]:
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise VersionError(f"journal/versions.csv columns must be {COLUMNS}")
    rows = [_row(raw, line) for line, raw in enumerate(reader, start=2)]
    _check_order(rows)
    return rows


def _row(raw: dict, line: int) -> VersionRow:
    where = f"journal/versions.csv line {line}"
    try:
        components = json.loads(raw["components"])
        row = VersionRow(raw["book"], raw["version_id"], date.fromisoformat(raw["starts_on"]),
                         raw["registered_in_commit"], components, raw["reason"])  # fmt: skip
    except (TypeError, ValueError) as bad:
        raise VersionError(f"{where}: unreadable row: {bad}") from None
    if not is_known_book(row.book):
        raise VersionError(f"{where}: unknown book {row.book!r}")
    if not row.version_id.strip() or not row.reason.strip():
        raise VersionError(f"{where}: version_id and reason must be filled")
    if not FULL_COMMIT.fullmatch(row.registered_in_commit):
        raise VersionError(f"{where}: registered_in_commit must be a full git commit id")
    if not isinstance(components, dict) or not components or not all(isinstance(v, str) for v in components.values()):
        raise VersionError(f"{where}: components must be a non-empty JSON object of text values")
    return row


def _check_order(rows: Sequence[VersionRow]) -> None:
    latest: dict[str, VersionRow] = {}
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if (row.book, row.version_id) in seen:
            raise VersionError(f"{row.book} {row.version_id}: registered twice")
        before = latest.get(row.book)
        if before and row.starts_on <= before.starts_on:
            raise VersionError(f"{row.book} {row.version_id}: starts on {row.starts_on}, not after {before.version_id}")
        seen.add((row.book, row.version_id))
        latest[row.book] = row


def render(rows: Sequence[VersionRow]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(row.as_csv() for row in rows)
    return out.getvalue()


class VersionRegistry:
    def __init__(self, path: Path):
        self.path = Path(path)

    def rows(self) -> list[VersionRow]:
        return parse_versions(self.path.read_text(encoding="utf-8")) if self.path.is_file() else []

    def append(self, row: VersionRow) -> None:
        """Adds one row after checking the whole registry with it; the existing bytes are kept as they are."""
        parse_versions(render([*self.rows(), row]))
        old = self.path.read_text(encoding="utf-8") if self.path.is_file() else render([])
        old += "" if old.endswith("\n") else "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(old + render([row]).split("\n", 1)[1], encoding="utf-8")
