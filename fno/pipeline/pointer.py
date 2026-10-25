"""What a download job tells a routine (story O6): which file, never its data. The routine receives the pointer as
untrusted text, so reading it back checks every field: a known dataset, an archive path inside the raw or revisions
area, a day as the batch and a SHA-256 as the version. Anything else is refused before Drive is touched."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from ..storage.raw_store import path_parts

POINTER_FIELDS = ("batch", "dataset", "path", "version")
READABLE_AREAS = ("raw", "revisions")
VERSION_PATTERN = re.compile(r"[0-9a-f]{64}")
BATCH_PATTERN = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]{0,63}")
MAX_POINTER_BYTES = 2048


class PointerRefused(ValueError):
    """The text is not a pointer this project wrote (wrong fields, unknown dataset or a path outside the archive)."""


@dataclass(frozen=True, order=True)
class BatchPointer:
    dataset: str  # archive dataset folder, e.g. nse/derivatives/participant-oi
    batch: str  # the day the file belongs to (YYYY-MM-DD)
    version: str  # SHA-256 of the file's bytes: a republished file is a new version
    path: str  # where the bytes are in the Drive project folder (raw/... or revisions/...)

    def to_text(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @property
    def key(self) -> str:
        """The record path of this batch and version, the same on the firing and the processing side."""
        return f"{self.dataset}/{self.batch}/{self.version}.json"


def parse_pointer(text: str, datasets: frozenset[str]) -> BatchPointer:
    """The pointer in `text`, or PointerRefused naming the first thing wrong with it."""
    if len(text.encode("utf-8")) > MAX_POINTER_BYTES:
        raise PointerRefused("longer than any pointer")
    try:
        fields = json.loads(text)
    except ValueError as error:
        raise PointerRefused(f"not JSON ({error.msg})") from None
    if not isinstance(fields, dict) or sorted(fields) != list(POINTER_FIELDS):
        raise PointerRefused(f"fields must be exactly {', '.join(POINTER_FIELDS)}")
    if not all(isinstance(value, str) for value in fields.values()):
        raise PointerRefused("every field must be text")
    pointer = BatchPointer(**fields)
    _check(pointer, datasets)
    return pointer


def _check(pointer: BatchPointer, datasets: frozenset[str]) -> None:
    if pointer.dataset not in datasets:
        raise PointerRefused(f"unknown dataset {pointer.dataset!r}")
    if not BATCH_PATTERN.fullmatch(pointer.batch):
        raise PointerRefused("batch is not a plain name")
    if not VERSION_PATTERN.fullmatch(pointer.version):
        raise PointerRefused("version is not a SHA-256")
    try:
        parts = path_parts(pointer.path)
    except ValueError:
        raise PointerRefused("path is not an archive path") from None
    if parts[0] not in READABLE_AREAS or not "/".join(parts[1:]).startswith(f"{pointer.dataset}/"):
        raise PointerRefused("path is outside the dataset's raw or revisions folder")
