"""When each of Groww's raw 3 pm quote files entered the real record (story REH1p): A4b keeps the file in Drive's raw
area only, with no O9 receipt and no manifest row; what vouches for it is its sidecar in `research/data/quotes`
(`csv_sha256`, `finished_at`), committed to `main`. A rehearsal sees the file once the replay clock has reached both
the attempt's `finished_at` and the committer time of the first commit on the record's `main` (first-parent) that
added the sidecar: the later of the two, so neither an early finish nor a late commit lets it be seen before the record
held it. The sidecar is read as that commit holds it (write-once), never from the record's working tree, which may be
on any branch. A sidecar saying the save failed (`raw_file_saved` false), one not on `main`, and any file outside
Groww's quote datasets never count.

The sidecars' commits are read once per record checkout and process (one `git log` over the quotes folder)."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from ..config import ROOT
from ..quotes.drive_only_store import QUOTE_FILE, SIDECAR
from ..quotes.recorder import DATASET, RAW_FILE_SAVED
from ..storage.wiring import QUOTES_FOLDER
from .manifest_rows import RAW_AREA, RECORD_MAIN

QUOTES = QUOTES_FOLDER.relative_to(ROOT)  # the record's sidecars
GROWW = f"{RAW_AREA}{DATASET.split('/')[0]}/"  # every Groww quote dataset (A4's, A4e's windows, A4f's weeklies)


class QuoteSidecars:
    def __init__(self, record: Path):
        self.record = Path(record)

    def seen_at(self, path: str) -> datetime | None:
        """When the record held this raw quote file, or None when no committed sidecar on main vouches for it."""
        if not (path.startswith(GROWW) and path.endswith(QUOTE_FILE)):
            return None
        sidecar = (QUOTES / path.removeprefix(RAW_AREA).removesuffix(QUOTE_FILE)).as_posix() + SIDECAR
        added = _added(self.record).get(sidecar)
        if added is None:
            return None
        committed, commit = added
        meta = json.loads(_git(self.record, "show", f"{commit}:{sidecar}"))
        if not meta.get(RAW_FILE_SAVED, True):
            return None
        return max(datetime.fromisoformat(meta["finished_at"]), committed)


@lru_cache(maxsize=4)
def _added(record: Path) -> dict[str, tuple[datetime, str]]:
    """Each sidecar path with the committer time and ID of the first-parent commit on main that added it (a merge
    counts from the merge, as in `manifest_rows`; a renamed file is a new file)."""
    try:
        log = _git(record, "log", "--first-parent", "--no-renames", "--diff-filter=A", "--name-only",
                   "--format=%x00%ct %H", RECORD_MAIN, "--", QUOTES.as_posix())  # fmt: skip
    except subprocess.CalledProcessError:  # no main in the record: nothing counts
        return {}
    added: dict[str, tuple[datetime, str]] = {}
    for entry in log.split("\0")[1:]:
        head, *paths = entry.strip().splitlines()
        stamp, commit = head.split()
        for name in paths:
            added[name] = (datetime.fromtimestamp(int(stamp), UTC), commit)  # newest first: the oldest is kept last
    return added


def _git(record: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=record, capture_output=True, text=True, check=True).stdout
