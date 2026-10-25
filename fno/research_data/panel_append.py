"""Appends new sessions to the NIFTY panel in place (story A13; G1 protocol v3 proposal, response 68).

The panel (story A3) only grows: a day is added only after the manifest's last day, never rebuilt or rewritten. Each
touched year file gets the new rows as one more gzip member (no header, no file name, zero time), so its old bytes stay
an exact prefix and every gzip reader still reads one CSV. The manifest keeps every existing entry as it was; it gains
the new days (A3's entry plus the stamp the caller gives, e.g. when and with which calendar it was appended), a later
`end`, and new hashes and row counts for the touched files only. Everything is written under temporary names and
swapped in at the end, the manifest last. A crash between those swaps leaves files that no longer match the manifest:
`verify` checks every file's SHA-256, content SHA-256 and row count against it, and the job runs it before anything
else, so an interrupted append is refused (fix: restore the committed panel, `git checkout research/data/nifty-panel/`),
never appended to again. In GitHub Actions the run commits only after a clean exit, so a crash publishes nothing.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .panel_rows import TABLE_COLUMNS
from .panel_store import GZIP_LEVEL, MANIFEST_FILE, PART_SUFFIX, TABLE_FILE, PanelDay, file_sha256

RESTORE = "restore the committed panel: git checkout research/data/nifty-panel/"
CHUNK = 1 << 20


class AppendRefused(RuntimeError):
    """The append would rewrite, reorder or mismatch the panel; nothing was written."""


def gzip_member(rows: Sequence[tuple[str, ...]], header: tuple[str, ...] | None = None) -> bytes:
    """One deterministic gzip member holding the rows (and the header, for a new file)."""
    text = io.StringIO()
    writer = csv.writer(text, lineterminator="\n")
    if header is not None:
        writer.writerow(header)
    writer.writerows(rows)
    return gzip.compress(text.getvalue().encode("utf-8"), compresslevel=GZIP_LEVEL, mtime=0)


class PanelAppender:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def manifest(self) -> dict:
        path = self.folder / MANIFEST_FILE
        if not path.is_file():
            raise AppendRefused(f"no {MANIFEST_FILE} in {self.folder}: build the panel with A3 first")
        return json.loads(path.read_text(encoding="utf-8"))

    def verify(self) -> None:
        """Every file the manifest lists has its recorded SHA-256, content SHA-256 and rows; AppendRefused otherwise."""
        manifest = self.manifest()
        for name, recorded in sorted(manifest["files"].items()):
            path = self.folder / name
            found = _fingerprint(path)
            wanted = (recorded["sha256"], recorded["csv_sha256"], recorded["rows"])
            if found != wanted:
                raise AppendRefused(f"{name} does not match {MANIFEST_FILE} (an interrupted append?): {RESTORE}")

    def last_day(self) -> date:
        return date.fromisoformat(self.manifest()["end"])

    def append(self, days: Sequence[PanelDay], stamp: dict) -> int:
        """Adds the days (in date order, all after the manifest's end); returns how many were added."""
        if not days:
            return 0
        manifest = self.manifest()
        self._check(manifest, days)
        files = self._grown_files(manifest, days)
        for name, data in files.items():
            text = gzip.decompress(data)
            manifest["files"][name] = {
                "sha256": file_sha256(data), "csv_sha256": file_sha256(text), "rows": text.count(b"\n") - 1,
            }  # fmt: skip
        for panel_day in days:
            manifest["days"][panel_day.day.isoformat()] = {**panel_day.entry, **stamp}
        manifest["end"] = days[-1].day.isoformat()
        self._swap_in(files, json.dumps(manifest, indent=1, sort_keys=True) + "\n")
        return len(days)

    def _check(self, manifest: dict, days: Sequence[PanelDay]) -> None:
        if manifest["columns"] != {table: list(columns) for table, columns in TABLE_COLUMNS.items()}:
            raise AppendRefused("the panel's columns are not A3's: appended rows would not match them")
        previous = manifest["end"]
        for panel_day in days:
            day = panel_day.day.isoformat()
            if day in manifest["days"] or day <= previous:
                raise AppendRefused(f"{day} is not after {previous}: panel days are only appended, never rewritten")
            previous = day
        for name in {self._name(table, d.day.year) for d in days for table, rows in d.rows.items() if rows}:
            self._require_unchanged(manifest, name)

    def _require_unchanged(self, manifest: dict, name: str) -> None:
        path, recorded = self.folder / name, manifest["files"].get(name)
        if recorded is None and not path.exists():
            return
        if recorded is None or not path.is_file() or file_sha256(path.read_bytes()) != recorded["sha256"]:
            raise AppendRefused(f"{name} does not match {MANIFEST_FILE} (an interrupted append?): {RESTORE}")

    def _grown_files(self, manifest: dict, days: Sequence[PanelDay]) -> dict[str, bytes]:
        rows: dict[str, list[tuple[str, ...]]] = {}
        for panel_day in days:
            for table, table_rows in panel_day.rows.items():
                if table_rows:
                    rows.setdefault(self._name(table, panel_day.day.year), []).extend(table_rows)
        grown = {}
        for name, new_rows in rows.items():
            path = self.folder / name
            if name in manifest["files"]:
                grown[name] = path.read_bytes() + gzip_member(new_rows)
            else:
                grown[name] = gzip_member(new_rows, TABLE_COLUMNS[name.split("_")[0]])
        return grown

    def _swap_in(self, files: dict[str, bytes], manifest_text: str) -> None:
        parts = {self.folder / name: self.folder / (name + PART_SUFFIX) for name in files}
        for final, part in parts.items():
            part.write_bytes(files[final.name])
        manifest_part = self.folder / (MANIFEST_FILE + PART_SUFFIX)
        manifest_part.write_text(manifest_text, encoding="utf-8")
        for final, part in parts.items():
            part.replace(final)
        manifest_part.replace(self.folder / MANIFEST_FILE)

    @staticmethod
    def _name(table: str, year: int) -> str:
        return TABLE_FILE.format(table=table, year=year)


def _fingerprint(path: Path) -> tuple[str, str, int] | None:
    """The file's SHA-256, its decompressed content's SHA-256 and its data rows (header excluded), read in chunks; None
    when the file is missing or not a whole gzip stream (a damaged file is a mismatch, never a crash)."""
    content, lines = hashlib.sha256(), 0
    try:
        with gzip.open(path, "rb") as stream:
            while chunk := stream.read(CHUNK):
                content.update(chunk)
                lines += chunk.count(b"\n")
    except (OSError, EOFError):  # missing, not gzip, or cut short
        return None
    return file_sha256(path.read_bytes()), content.hexdigest(), lines - 1
