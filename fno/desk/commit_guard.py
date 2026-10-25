"""The paper desk's last check before any commit (story E2b; owner "6 A" and "8 A", 15 Oct 2026): a raw Groww quote
file (`<quotes folder>/groww/**/*.csv`: every Groww quote dataset, A4e's named windows included) is never committed to
the public repository. Paths are compared after resolving them, so an upper-case `.CSV`, a `../` path into the folder
or a symlink pointing into it is caught too. The capture's sidecar (`.meta.json`) and the day's `.canonical` marker
are not quote files and pass."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..quotes.recorder import DATASET

GROWW_QUOTES = DATASET.split("/", 1)[0]  # `groww`: the .gitignore rule and the record scan cover the same folder

QUOTE_FILE_SUFFIX = ".csv"
REFUSED = "refused: {paths} would publish raw Groww quotes (owner 6 A and 8 A); nothing was committed"


class RawQuoteCommitRefused(ValueError):
    """A commit would have included a raw Groww quote file; the message names it."""


class RawQuoteGuard:
    def __init__(self, root: Path, quotes_folder: Path):
        self.root, self.folder = Path(root), (Path(quotes_folder) / GROWW_QUOTES).resolve()

    def check(self, paths: Sequence[Path]) -> None:
        raw = [str(p) for p in paths if self._is_raw_quote_file(p)]
        if raw:
            raise RawQuoteCommitRefused(REFUSED.format(paths=", ".join(raw)))

    def _is_raw_quote_file(self, path: Path) -> bool:
        resolved = (path if Path(path).is_absolute() else self.root / path).resolve()
        return resolved.suffix.lower() == QUOTE_FILE_SUFFIX and resolved.is_relative_to(self.folder)
