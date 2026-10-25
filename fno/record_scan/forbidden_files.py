"""Files that must never be committed whatever they hold (story A4b): the public-record scan (story O5) refuses them by
path, as one finding naming the kind, so a raw Groww quote file, a private paper account file (story E2d) or a data
file moved to Drive (story O9b) is refused even when added with `git add -f`."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ForbiddenFiles:
    kind: str
    folder: str  # repository path prefix, ending with "/"
    suffix: str

    def matches(self, path: str) -> bool:
        return path.startswith(self.folder) and path.lower().endswith(self.suffix)


RAW_GROWW_QUOTES = ForbiddenFiles(
    "raw Groww quote file (Google Drive only, story A4b)", "research/data/quotes/groww/", ".csv"
)
MOVED_VIX_FILES = ForbiddenFiles(  # O9b step 1: the table and checks are write-once in Drive, their receipts here
    "India VIX data moved to Drive (receipts only, story O9b)", "research/data/vix/", ".csv"
)


@dataclass(frozen=True)
class ForbiddenFolders:
    """Every file under any folder matching one of `patterns` (repository paths, `*` one folder name), for folders
    one fixed prefix cannot name: each book's and each shadow account's `account/` folder."""

    kind: str
    patterns: tuple[str, ...]

    def matches(self, path: str) -> bool:
        return any(_folder_regex(pattern).match(path) for pattern in self.patterns)


def _folder_regex(pattern: str) -> re.Pattern:
    """`journal/*/account/` as a prefix regex: each `*` is exactly one folder name, the rest literal."""
    return re.compile("[^/]+".join(re.escape(part) for part in pattern.split("*")))


PAPER_ACCOUNT_FILES = ForbiddenFolders(
    "private paper account file (Google Drive only, stories E2c and E2d)",
    ("journal/*/account/", "journal/shadow/*/account/", "journal/school/"),  # MS-P1d: every school driver account
)
