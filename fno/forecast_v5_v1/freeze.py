"""`research/forecasts/v5/FREEZE_v5_v1.md` (story G14, criteria 9 and 12; judge 596 addendum 2): its text, written
once after `FREEZE_v4.md`, and the check the capture runs before a live row. Byte-checked: `method.freeze_files`, each
with its SHA-256 and whether `FREEZE_v4.md` has the same row ("v4 row") or none ("v5 only"); a file with a different
v4 row refuses the record. Recorded, not checked: `method.SHARED`, each with its SHA-256. The check refuses a missing
record, one without a `Frozen on:` line, a changed byte, and a byte-checked list other than today's walk (fail
closed: a newly walked file must be frozen by a new record)."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path

from .method import FREEZE_STARTS, freeze_files, recorded

FUTURE = "{name} is frozen on {day}, after today: no live row before it"

V4_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", re.MULTILINE)  # FREEZE_v4.md's table row
CHECKED_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \| (v4 row|v5 only) \|$", re.MULTILINE)
FROZEN_ON = re.compile(r"^Frozen on: (\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
V4_ROW_LABEL, V5_ONLY = "v4 row", "v5 only"
TITLE = "# FREEZE_v5_v1: story G14's frozen files"
RV_TABLE_NOTE = (
    "`fno/intraday/rv_table.py` is byte-checked here although `FREEZE_v4.md` only records it (judge 596 addendum 2)."
)


class NotFrozen(RuntimeError):
    """A planned state: no record yet (or not written, for `freeze`); the capture writes nothing and is `refused`."""


class FreezeBroken(RuntimeError):
    """A fault: the record no longer matches the tree or cannot be read; the capture writes nothing and `failed`
    (story G14, amendment 2: revert the edit or write a new record version)."""


def sha256(root: Path, relative: str) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def record_text(root: Path, v4_record: str, v4_checked: list[str], frozen_on: date) -> str:
    """The record's text; refuses when a file v4's freeze byte-checks (`v4_checked`, `freeze_check.byte_checked`) has
    no row in `v4_record` (an empty or changed v4 record must not pass as "v5 only") or a row other than its bytes."""
    v4 = dict(V4_ROW.findall(v4_record))
    rows = []
    for relative in freeze_files(root):
        digest = sha256(root, relative)
        if relative in v4_checked and relative not in v4:
            raise NotFrozen(f"{relative}: v4's freeze checks it, but FREEZE_v4.md has no row for it")
        if relative in v4 and v4[relative] != digest:
            raise NotFrozen(f"{relative}: its bytes differ from its FREEZE_v4.md row")
        rows.append(f"| `{relative}` | `{digest}` | {V4_ROW_LABEL if relative in v4 else V5_ONLY} |")
    shared = [f"| `{relative}` | `{sha256(root, relative)}` |" for relative in recorded(root, FREEZE_STARTS)]
    return "\n".join([
        TITLE, "", f"Frozen on: {frozen_on.isoformat()}", "", "## Byte-checked", "", "| File | SHA-256 | v4 |",
        "|---|---|---|", *rows, "", RV_TABLE_NOTE, "", "## Recorded, not checked", "", "| File | SHA-256 |",
        "|---|---|", *shared, "",
    ])  # fmt: skip


def check(root: Path, record: Path) -> date:
    """The record's `Frozen on:` day when it holds; NotFrozen when it is missing, FreezeBroken when it no longer
    matches."""
    if not record.is_file():
        raise NotFrozen(f"{record.name} is missing")
    text = record.read_text(encoding="utf-8")
    frozen_on = FROZEN_ON.search(text)
    if frozen_on is None:
        raise FreezeBroken(f"{record.name} has no 'Frozen on: YYYY-MM-DD' line")
    listed = {path: digest for path, digest, _ in CHECKED_ROW.findall(text)}
    if sorted(listed) != freeze_files(root):
        raise FreezeBroken(f"{record.name} lists other files than today's walk: a new record is needed")
    changed = [path for path, digest in listed.items() if sha256(root, path) != digest]
    if changed:
        raise FreezeBroken(f"{changed[0]} differs from {record.name}")
    try:
        return date.fromisoformat(frozen_on.group(1))
    except ValueError as bad:
        raise FreezeBroken(f"{record.name}: 'Frozen on: {frozen_on.group(1)}' is not a date") from bad
