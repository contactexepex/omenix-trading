"""A book's private pack (story E2, design 13.5 step 2): the book's own files as they stand at build time, each with
its path, SHA-256 and text. Book 1 and Book 2 read their account folder and the playbook; Book 3 reads its account
folder and its constitution and strategy registry (`book3/`). A file is taken only if it resolves inside one of its
book's allowed folders, so a link or `..` can never pull in another book's account. The book's own packs folder is
left out (a pack never contains packs), and so are dot files such as the account lock's lease."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..constants import BOOK1_RULES, BOOK2_HYBRID, BOOK3_AI, BOOK3_FOLDER, JOURNAL_FOLDER, PACKS_FOLDER, PLAYBOOK_FOLDER
from .pack_items import PackError, canonical_json, sha256_hex

SCHEMA_VERSION = 1
EVALUATION = "evaluation"  # the book's sheet (story E2e), present only for a book that has one
ALLOWED_FOLDERS = {
    BOOK1_RULES: (f"{JOURNAL_FOLDER}/{BOOK1_RULES}", PLAYBOOK_FOLDER),
    BOOK2_HYBRID: (f"{JOURNAL_FOLDER}/{BOOK2_HYBRID}", PLAYBOOK_FOLDER),  # its envelope lives beside the playbook (D4)
    BOOK3_AI: (f"{JOURNAL_FOLDER}/{BOOK3_AI}", BOOK3_FOLDER),  # constitution and strategy registry (D5)
}


@dataclass(frozen=True)
class PrivatePack:
    book: str
    day: date
    body: dict

    @property
    def data(self) -> bytes:
        return canonical_json(self.body)

    @property
    def sha256(self) -> str:
        return sha256_hex(self.data)


def _hidden(relative: Path) -> bool:
    """Dot files are operational, not records: the account's `.lock` lease (host, process) never enters a pack."""
    return any(part.startswith(".") for part in relative.parts)


class PrivatePackBuilder:
    def __init__(self, root: Path, allowed: Mapping[str, Sequence[str]] = ALLOWED_FOLDERS):
        self.root, self.allowed = Path(root), {book: tuple(folders) for book, folders in allowed.items()}

    def build(self, book: str, day: date, evaluation: Mapping | None = None) -> PrivatePack:
        """`evaluation`: the book's sheet (story E2e), under "evaluation"; a book without one is unchanged."""
        if book not in self.allowed:
            raise PackError(f"unknown book {book!r}")
        files = [self._file(path, folder) for folder in self.allowed[book] for path in self._paths(book, folder)]
        body = {"schema_version": SCHEMA_VERSION, "kind": "book_private_pack", "book": book, "day": day.isoformat(),
                "files": sorted(files, key=lambda f: f["path"])}  # fmt: skip
        if evaluation is not None:
            body[EVALUATION] = dict(evaluation)
        return PrivatePack(book, day, body)

    def _paths(self, book: str, folder: str) -> list[Path]:
        base = self.root / folder
        if not base.is_dir():
            return []
        own_packs = self.root / JOURNAL_FOLDER / book / PACKS_FOLDER
        return sorted(
            p for p in base.rglob("*")
            if p.is_file() and not p.is_relative_to(own_packs) and not _hidden(p.relative_to(base))
        )  # fmt: skip

    def _file(self, path: Path, folder: str) -> dict:
        allowed = (self.root / folder).resolve()
        if not path.resolve().is_relative_to(allowed):
            raise PackError(f"{path} resolves outside its book's folder {folder}: refused")
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise PackError(f"{path} is not text: a private pack holds text records only") from None
        return {"path": path.relative_to(self.root).as_posix(), "sha256": sha256_hex(data), "text": text}
