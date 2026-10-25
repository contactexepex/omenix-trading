"""SHA-256 receipts of Drive files (story O9, rule 3): one small file per Drive file under `receipts/` in the
repository, so the data lives only in Drive while GitHub keeps what proves it and when it was published. One file per
write means two runs never touch the same receipt, so a merge cannot conflict. A receipt is written once: the same
digest again keeps the first one (its time is the evidence); a different digest is refused."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .raw_store import RawFileConflict, path_parts

RECEIPT_SUFFIX = ".sha256"
FIELD_SEPARATOR = "\t"


@dataclass(frozen=True)
class Receipt:
    path: str  # the Drive path, area included (e.g. `data/intraday/...`)
    sha256: str
    size: int
    written_at: str  # UTC, ISO 8601 with offset
    writer: str  # the job or command that wrote the file
    run_id: str

    def to_text(self) -> str:
        fields = (self.sha256, str(self.size), self.written_at, self.writer, self.run_id)
        return FIELD_SEPARATOR.join(fields) + "\n"

    @classmethod
    def from_text(cls, path: str, text: str) -> Receipt:
        sha256, size, written_at, writer, run_id = text.rstrip("\n").split(FIELD_SEPARATOR)
        return cls(path, sha256, int(size), written_at, writer, run_id)


class ReceiptFolder:
    """The `receipts/` tree of a checkout: `receipts/<drive path>.sha256`."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def file_for(self, path: str) -> Path:
        *folders, name = path_parts(path)
        return self.folder.joinpath(*folders, name + RECEIPT_SUFFIX)

    def read(self, path: str) -> Receipt | None:
        file = self.file_for(path)
        return Receipt.from_text(path, file.read_text()) if file.is_file() else None

    def write(self, receipt: Receipt) -> Receipt:
        """The receipt kept for the path: the earlier one when the digest matches, else the new one."""
        existing = self.read(receipt.path)
        if existing is not None:
            if existing.sha256 != receipt.sha256:
                raise RawFileConflict(f"{receipt.path} already has a receipt with a different SHA-256")
            return existing
        file = self.file_for(receipt.path)
        file.parent.mkdir(parents=True, exist_ok=True)
        temporary = file.with_name(f".{file.name}.part")
        temporary.write_text(receipt.to_text())
        temporary.replace(file)
        return receipt

    def under(self, prefix: str) -> list[Receipt]:
        """Every receipt under the folder `prefix`, in path order; `prefix` naming one receipted file gives that file
        (a caller asking for one file never gets nothing silently, 23 Oct 2026)."""
        single = self.read(prefix)
        if single is not None:
            return [single]
        root = self.folder.joinpath(*path_parts(prefix))
        if not root.is_dir():
            return []
        files = sorted(f for f in root.rglob(f"*{RECEIPT_SUFFIX}") if not f.name.startswith("."))
        return [self.read(self._drive_path(f)) for f in files]

    def _drive_path(self, file: Path) -> str:
        return file.relative_to(self.folder).as_posix()[: -len(RECEIPT_SUFFIX)]
