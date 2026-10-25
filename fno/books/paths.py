"""Where a book's account lives, and the firewall that keeps every account object inside its own book (E1 criterion 6,
design 12.6: books never share money, positions or results)."""

from __future__ import annotations

import re
from pathlib import Path

from ..constants import BOOKS, JOURNAL_FOLDER, SHADOW_FOLDER, SHADOW_PREFIX

ACCOUNT_FOLDER = "account"
SHADOW_VERSION = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*-v[1-9][0-9]*")  # a playbook version: <name>-v<n> (story D1)


class BookPathError(ValueError):
    """A book name that is not one of the three books, or a path that leaves the book's own account folder."""


def shadow_account(version: str) -> str:
    """The account name of a shadow version's forward test, e.g. `shadow:example-sc-v1`."""
    return SHADOW_PREFIX + version


def book_folder(root: Path, book: str) -> Path:
    """`<root>/journal/<book>` for one of the three books, or `<root>/journal/shadow/<name>-v<n>` for a shadow version
    (`shadow:<name>-v<n>`); anything else is refused."""
    if book in BOOKS:
        return Path(root) / JOURNAL_FOLDER / book
    version = book.removeprefix(SHADOW_PREFIX)
    if book.startswith(SHADOW_PREFIX) and SHADOW_VERSION.fullmatch(version):
        return Path(root) / JOURNAL_FOLDER / SHADOW_FOLDER / version
    raise BookPathError(f"unknown book {book!r}; the books are {', '.join(BOOKS)} or {SHADOW_PREFIX}<name>-v<n>")


def account_folder(root: Path, book: str) -> Path:
    """`<root>/journal/<book>/account` for one of the three books; anything else is refused."""
    return book_folder(root, book) / ACCOUNT_FOLDER


def file_in_account(folder: Path, name: str) -> Path:
    """A file directly inside the account folder. Refuses separators, `..` and any path that resolves (through a
    symbolic link, say) outside the folder, so no code path reaches another book's files through an account object."""
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise BookPathError(f"{name!r} is not a plain file name inside the account folder")
    path = folder / name
    if not path.resolve().is_relative_to(folder.resolve()) or not _folder_is_its_own(folder):
        raise BookPathError(f"{path} resolves outside its book's account folder {folder}")
    return path


def _folder_is_its_own(folder: Path) -> bool:
    """The account folder itself must not be a link into another book (journal/book1_rules/account -> book2's)."""
    resolved = folder.resolve()
    return resolved.name == folder.name and resolved.parent.name == folder.parent.name
