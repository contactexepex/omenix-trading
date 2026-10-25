"""Every reader reads Drive through this cache (story O9, rule 4). The receipts are the index: only a file with a
receipt counts, it is downloaded only when the cache lacks it or holds other bytes, and every byte is checked against
the receipt's SHA-256 before it is used. A file Drive does not return, or returns with other bytes, is reported and
never written, so a reader stops instead of using it. `sync(..., into=...)` also writes files back to their original
repository paths (git-ignored) for the frozen checks that hash the working tree (O9 section 4.1)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .raw_store import RawFileStore, path_parts
from .receipts import ReceiptFolder

MISSING = "{path}: in the receipts, not returned by Drive"
DAMAGED = "{path}: Drive's bytes do not match the receipt's SHA-256"
NO_RECEIPTS = "{prefix}: no receipts under it (neither a receipted file nor a folder holding one)"


@dataclass
class SyncReport:
    present: int = 0
    downloaded: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.problems


class DriveCache:
    def __init__(self, drive: RawFileStore, receipts: ReceiptFolder, root: Path):
        """`drive`: the whole project folder (paths include the area); `root`: the cache folder on disk."""
        self.drive, self.receipts, self.root = drive, receipts, Path(root)

    def local(self, path: str, into: Path | None = None) -> Path:
        """Where a Drive path lives on disk: under the cache, or under `into` with the same relative path."""
        return (into or self.root).joinpath(*path_parts(path))

    def sync(self, prefix: str, into: Path | None = None, strip: str = "") -> SyncReport:
        """Brings every receipted file under `prefix` (a folder, or one receipted file) to disk, verified; a prefix
        with no receipt at all is a problem, never an empty success. `strip` drops a leading part of the Drive
        path when writing under `into` (e.g. the area, to restore `data/research/x` as `research/x`)."""
        report, receipts = SyncReport(), self.receipts.under(prefix)
        if not receipts:  # a wrong path must never read as "nothing to sync, all verified"
            report.problems.append(NO_RECEIPTS.format(prefix=prefix))
        for receipt in receipts:
            target = self.local(receipt.path.removeprefix(strip), into)
            if target.is_file() and _sha256(target.read_bytes()) == receipt.sha256:
                report.present += 1
                continue
            data = self.drive.get(receipt.path)
            if data is None:
                report.problems.append(MISSING.format(path=receipt.path))
            elif _sha256(data) != receipt.sha256:
                report.problems.append(DAMAGED.format(path=receipt.path))
            else:
                _write(target, data)
                report.downloaded.append(receipt.path)
        return report


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(file: Path, data: bytes) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_name(f".{file.name}.part")
    temporary.write_bytes(data)
    temporary.replace(file)  # a reader never sees a half-written file under the real name
