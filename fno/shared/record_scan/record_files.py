"""Which files the public-record scan reads (story O5): the committed files, the files staged for a commit, or files
named explicitly (a session export before it is sent). Code files are read too, and marked as code."""

from __future__ import annotations

import gzip
import io
import subprocess
import zipfile
import zlib
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# Code folders: they hold the scan's own patterns and the tests' planted examples, so they are scanned only for
# credential-shaped values (keys and tokens). Everything else tracked is a record and gets every pattern, so a new
# record folder (journal/, playbook/, agents/, book3/ ...) is scanned without being listed anywhere.
CODE_FOLDERS = ("fno/", "tests/", "tools/")
TRACKED_FILES = ("git", "ls-files", "-z")
# Staged entries with their mode and blob id: ":<old mode> <new mode> <old id> <new id> <status>\0<path>\0"
STAGED_ENTRIES = ("git", "diff", "--cached", "--raw", "-z", "--full-index", "--no-renames", "--diff-filter=ACMR")
STAGED_BLOB = ("git", "cat-file", "blob")  # + "<id>": the staged bytes, which are what the commit will hold
GITLINK_MODE = "160000"  # a nested repository (submodule or agent worktree): a commit id, no content to scan


@dataclass(frozen=True)
class RecordText:
    path: str
    text: str
    is_code: bool = False
    unreadable: bool = False  # a damaged archive: reported as a finding, never skipped


ARCHIVE_ERRORS = (OSError, EOFError, zlib.error, zipfile.BadZipFile)


def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def texts_of(path: str, data: bytes, is_code: bool = False) -> list[RecordText]:
    """The file's text; gzip files are unpacked, and each member of a zip file is one text named `<zip>/<member>`
    (their content is committed too). A damaged archive gives one unreadable text, so the scan refuses it."""
    try:
        return _texts_of(path, data, is_code)
    except ARCHIVE_ERRORS:
        return [RecordText(path, "", is_code, unreadable=True)]


def _texts_of(path: str, data: bytes, is_code: bool) -> list[RecordText]:
    if path.endswith(".gz"):
        return [RecordText(path, _decode(gzip.decompress(data)), is_code)]
    if path.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return [
                RecordText(f"{path}/{name}", _decode(archive.read(name)), is_code)
                for name in archive.namelist()
                if not name.endswith("/")
            ]
    return [RecordText(path, _decode(data), is_code)]


def is_code(path: str) -> bool:
    return path.startswith(CODE_FOLDERS)


class RecordSource(ABC):
    @abstractmethod
    def records(self) -> Iterator[RecordText]:
        """Each file to scan, with its text."""


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(args, cwd=root, check=True, capture_output=True).stdout


def _paths(output: bytes) -> list[str]:
    return [p for p in output.decode("utf-8").split("\0") if p]


class TrackedRecords(RecordSource):
    """Every file git tracks, as it is in the working tree."""

    def __init__(self, root: Path):
        self._root = root

    def records(self) -> Iterator[RecordText]:
        for path in _paths(_git(self._root, *TRACKED_FILES)):
            file = self._root / path
            if file.is_file():  # deleted in the working tree but not yet in the index
                yield from texts_of(path, file.read_bytes(), is_code(path))


def staged_blobs(output: bytes) -> list[tuple[str, str]]:
    """(path, blob id) of each staged file; gitlinks are left out because they hold no content of this repository."""
    fields = output.decode("utf-8").split("\0")
    entries = zip(fields[0::2], fields[1::2])  # (":<modes> <ids> <status>", path) pairs
    return [(path, info.split()[3]) for info, path in entries if info.split()[1] != GITLINK_MODE]


class StagedRecords(RecordSource):
    """The files staged for the next commit, exactly as the commit will hold them."""

    def __init__(self, root: Path):
        self._root = root

    def records(self) -> Iterator[RecordText]:
        for path, blob in staged_blobs(_git(self._root, *STAGED_ENTRIES)):
            yield from texts_of(path, _git(self._root, *STAGED_BLOB, blob), is_code(path))


class NamedFiles(RecordSource):
    """Files named on the command line (whole folders included), wherever they are; all are records."""

    def __init__(self, paths: list[Path]):
        self._paths = paths

    def records(self) -> Iterator[RecordText]:
        for given in self._paths:
            files = sorted(p for p in given.rglob("*") if p.is_file()) if given.is_dir() else [given]
            for file in files:
                yield from texts_of(file.as_posix(), file.read_bytes())
