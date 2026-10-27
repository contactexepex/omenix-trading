"""SHA-256 receipts of Drive files (story O9, rule 3): one small file per Drive file under `receipts/` in the
repository, so the data lives only in Drive while GitHub keeps what proves it and when it was published. One file per
write means two runs never touch the same receipt, so a merge cannot conflict. A receipt is written once: the same
digest again keeps the first one (its time is the evidence); a different digest is refused."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from fno.ingestion.storage.batch_receipts import BATCH_FOLDER, PER_FILE_CONFLICT, BatchIndex, BatchProblem, covers
from fno.ingestion.storage.raw_store import RawFileConflict, path_parts
from fno.ingestion.storage.receipt import FIELD_SEPARATOR, Receipt

RECEIPT_SUFFIX = ".sha256"
__all__ = ["FIELD_SEPARATOR", "RECEIPT_SUFFIX", "Receipt", "ReceiptFolder"]  # Receipt: where callers import it from


class ReceiptWriter(Protocol):
    """How a store saves a receipt (story R2): one file per Drive file (`ReceiptFolder`) or one batch file per run
    (`BatchReceiptWriter`). Both keep the first receipt of a path and refuse a different digest for it."""

    def write(self, receipt: Receipt) -> Receipt: ...


class ReceiptFolder:
    """The `receipts/` tree of a checkout: `receipts/<drive path>.sha256`, and the batch files of runs that packed
    their receipts (`receipts/_batches/`, story R2). Reading finds a file's receipt in either; writing here is the
    one-file-per-receipt strategy."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.batches = BatchIndex(self.folder / BATCH_FOLDER)

    def file_for(self, path: str) -> Path:
        *folders, name = path_parts(path)
        return self.folder.joinpath(*folders, name + RECEIPT_SUFFIX)

    def read(self, path: str) -> Receipt | None:
        file = self.file_for(path)
        if file.is_file():
            return Receipt.from_text(path, file.read_text())
        return self.batches.receipts().get(path)

    def batch_problems(self, prefix: str) -> list[BatchProblem]:
        """What is wrong with the batch files, as far as a sync of `prefix` should hear of it: a damaged line, two
        digests for one path (in batches, or between a batch and a per-file receipt)."""
        found = [p for p in self.batches.problems() if covers(prefix, p.path)]
        for path, batched in self.batches.receipts().items():
            per_file = self.file_for(path)
            if covers(prefix, path) and per_file.is_file() and self.read(path).sha256 != batched.sha256:
                found.append(BatchProblem(PER_FILE_CONFLICT.format(path=path), path))
        return found

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
        parts = tuple(path_parts(prefix))
        root = self.folder.joinpath(*parts)
        files = (
            sorted(f for f in root.rglob(f"*{RECEIPT_SUFFIX}") if not f.name.startswith(".")) if root.is_dir() else []
        )
        found = [self.read(self._drive_path(f)) for f in files]
        batched = {p: r for p, r in self.batches.receipts().items() if tuple(path_parts(p))[: len(parts)] == parts}
        if not batched:
            return found
        merged = {**batched, **{r.path: r for r in found}}  # a per-file receipt, if there is one, is the one read
        return [merged[path] for path in sorted(merged)]

    def _drive_path(self, file: Path) -> str:
        return file.relative_to(self.folder).as_posix()[: -len(RECEIPT_SUFFIX)]
