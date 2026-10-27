"""The private materiality file (NP5b): `materiality/materiality-vN.json` in the private config area of the Drive, with
the discipline of every versioned private file (`news/versioned.py`): the newest version is used, none older than one
already used, a version edited in place is skipped loudly, errors are fixed codes. The terms are the owner's content;
none is shipped in code or in the repository (a starting set is a go-live item for the owner)."""

from __future__ import annotations

from collections.abc import Mapping

from fno.ingestion.news import codes
from fno.ingestion.news.materiality.terms import MaterialityError, MaterialTerms, parse_terms
from fno.ingestion.news.versioned import ErrorCodes, VersionedFiles
from fno.ingestion.storage.raw_store import RawFileStore

MATERIALITY_FOLDER = "materiality"


class PrivateMaterialityFile:
    def __init__(self, store: RawFileStore, lowest_version: int = 0, used: Mapping[int, str] | None = None):
        """`store`: the private config area (read only)."""
        self.files = VersionedFiles(
            store, MATERIALITY_FOLDER, "materiality",
            ErrorCodes(codes.MATERIALITY_MISSING, codes.MATERIALITY_ROLLED_BACK, codes.MATERIALITY_DAMAGED),
            MaterialityError,
        )  # fmt: skip
        self.lowest_version, self.used = lowest_version, used

    def terms(self) -> MaterialTerms:
        picked = self.files.latest(self.lowest_version, self.used)
        return parse_terms(picked.data, picked.version)
