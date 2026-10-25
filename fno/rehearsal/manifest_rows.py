"""When each manifest row entered the real record (REH1g, DRY2's gap G2): the A9 datasets and the global cues keep
their SHA-256 rows in `research/data/manifests/**/*.csv`, not in O9 receipts. A row counts from the committer time of
the first commit on the record's `main` (first-parent history, `git blame --first-parent` of `origin/main`) that holds
it, so a rehearsal sees a librarian or cue file only once the replay clock reaches that commit: never before (no
look-ahead). A row only in the working tree, or only on a branch not merged into `main`, never counts.

Two row shapes, each matched by its own writer's rule:
- a `path` column in a snapshot log (`global-cues/`, `groww-candles/`): the Drive path inside the raw area, matched
  whole (the revision logs and the filings lists also have a `path` column, naming a file someone else archived:
  never read);
- A9's `date,url,...` (`ManifestFolder`): a Drive path is its dataset's (day, URL) as the dataset's source names it
  (`day_for_path`, `url_for`: `Fingerprint.of`'s rule), so the same URL fetched on two days is two files. Each row
  keeps its dataset and SHA-256 too (`A9Row`), so REH1h's recorded archive can serve the copy a URL's row names.

The rows are read once per record checkout and process (`git blame` on about 55 files takes a few seconds)."""

from __future__ import annotations

import csv
import io
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path

from ..storage.source_lists import RAW_SOURCES, dataset_name

MANIFESTS = Path("research/data/manifests")
RAW_AREA = "raw/"  # the area the manifests describe (`storage.wiring.RAW_AREA`)
RECORD_MAIN = "origin/main"  # the record checkout's view of main (`checkout.RECORD_MAIN`)


@dataclass(frozen=True, order=True)
class A9Row:
    """One A9 manifest row as main first held it; ordered by its commit time first."""

    committed: datetime
    dataset: str  # the manifest's name (`dataset_name`)
    day: date
    url: str
    sha256: str


class ManifestRows:
    def __init__(self, record: Path):
        self.record = Path(record)

    def seen_at(self, path: str) -> datetime | None:
        """When the row naming this Drive path reached the record's main, or None when no row there names it."""
        if not path.startswith(RAW_AREA):
            return None
        inside = path.removeprefix(RAW_AREA)
        paths, files = _index(self.record)
        found = paths.get(inside)
        if found is not None:
            return found
        row = files.get(_a9_key(inside))
        return None if row is None else row.committed

    def archived(self, url: str) -> list[A9Row]:
        """Every A9 row on the record's main for this URL (any dataset, any day), earliest commit first."""
        _, files = _index(self.record)
        return sorted(row for row in files.values() if row.url == url)


def _a9_key(path: str) -> tuple[str, date, str] | None:
    """The (manifest, day, URL) row an A9 dataset's archive path is recorded under, or None for any other path."""
    for source in RAW_SOURCES:
        if path.startswith(f"{source.dataset}/"):
            try:
                return dataset_name(source), source.day_for_path(path), source.url_for(path)
            except ValueError:
                return None
    return None


@lru_cache(maxsize=4)
def _index(record: Path) -> tuple[dict[str, datetime], dict[tuple[str, date, str], A9Row]]:
    """Only the rows a file's own writer committed: its snapshot log's `path` rows (the files directly in each log
    folder) and its A9 dataset's `date,url` rows (one manifest per `RAW_SOURCES` entry). A revision log's or a
    filings list's `path` names a file another writer archived, so it never dates that file (judges 572 and 574)."""
    folder = record / MANIFESTS
    paths: dict[str, datetime] = {}
    files: dict[tuple[str, date, str], A9Row] = {}
    for manifest in sorted(m for log in _path_logs() for m in (folder / log).glob("*.csv")):
        for row, committed in _rows(record, manifest):
            if row.get("path"):
                _keep(paths, row["path"].strip("/"), committed)
    for name in sorted({dataset_name(source) for source in RAW_SOURCES}):
        for row, committed in _rows(record, folder / f"{name}.csv"):
            if row.get("url") and row.get("date"):
                day = date.fromisoformat(row["date"])
                _keep(files, (name, day, row["url"]), A9Row(committed, name, day, row["url"], row.get("sha256", "")))
    return paths, files


def _path_logs() -> tuple[str, ...]:
    """The snapshot logs' folders, as their writers name them (A17's global cues, A16b's Groww candles)."""
    from ..global_cues.wiring import SNAPSHOT_LOG_FOLDER
    from ..intraday.backfill_daily import MANIFESTS as CANDLE_MANIFESTS

    return SNAPSHOT_LOG_FOLDER.name, CANDLE_MANIFESTS.as_posix()


def _rows(record: Path, manifest: Path):
    """Each data row of the manifest as `main` holds it, with the committer time of its first-parent commit."""
    if not manifest.is_file():  # a dataset with no manifest yet: no row
        return
    relative = manifest.relative_to(record).as_posix()
    blame = subprocess.run(["git", "blame", "--first-parent", "--line-porcelain", RECORD_MAIN, "--", relative],
                           cwd=record, capture_output=True, text=True, check=False)  # fmt: skip
    if blame.returncode != 0:  # not on main (yet): no row of it counts
        return
    header = None
    for committed, text in _blamed(blame.stdout):
        if header is None:
            header = next(csv.reader([text]))
        elif text.strip():
            yield dict(zip(header, next(csv.reader(io.StringIO(text))), strict=False)), committed


def _blamed(porcelain: str) -> list[tuple[datetime, str]]:
    found, committed = [], datetime.min.replace(tzinfo=UTC)
    for line in porcelain.splitlines():
        if line.startswith("\t"):
            found.append((committed, line[1:]))
        elif line.startswith("committer-time "):
            committed = datetime.fromtimestamp(int(line.split()[1]), UTC)
    return found


def _keep(index: dict, key, found) -> None:
    """The earliest commit's entry (a commit time, or an `A9Row`, which orders by its commit time first)."""
    if key not in index or found < index[key]:
        index[key] = found
