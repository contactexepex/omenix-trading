"""The Staging area (docs/PIPELINE_DESIGN.md): where every fetch lands before anything trusts it. A fetcher writes
here and nowhere else; only the promotion gate turns a staged file into a record.

Layout `<source>/<fetch time>/<archive path>`, e.g. `nse/20261026T153000Z/nse/fo/participant_oi/2026/10/x.csv`. Every
fetch is a new write-once object, so a newer fetch of the same file is a new copy beside the old one (nothing is
overwritten, which the Drive stores cannot do for raw files anyway) and the copy's source and fetch time are in its
path. Staging holds raw, unchecked bytes: garbage may land here and is rejected by the gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fno.ingestion.storage.raw_store import RawFileStore, path_parts

STAMP_FORMAT = "%Y%m%dT%H%M%SZ"


@dataclass(frozen=True)
class StagedCopy:
    source: str  # who fetched it (a source tag such as "nse")
    fetched_at: datetime  # UTC
    path: str  # the archive path the record will use
    data: bytes


def stamp_of(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime(STAMP_FORMAT)


def _parse_stamp(name: str) -> datetime | None:
    try:
        return datetime.strptime(name, STAMP_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None  # not one of our fetch folders


class StagingArea:
    def __init__(self, store: RawFileStore):
        """`store`: the `staging` area of the project folder (the wiring passes an AreaStore, so this class cannot
        reach any other area)."""
        self.store = store

    def stage(self, source: str, path: str, data: bytes, fetched_at: datetime) -> bool:
        """Saves one fetch; False (nothing written) when the newest staged copy of this file already has these bytes."""
        path_parts(source)
        latest = self.latest(source, path)
        if latest and latest.data == data:
            return False
        self.store.put(f"{source}/{stamp_of(fetched_at)}/{path}", data)
        return True

    def copies(self, source: str, path: str) -> list[StagedCopy]:
        """The staged copies of an archive path from one source, earliest fetch first: the order the gate promotes in
        (the first passing copy becomes the record, as the first archived copy does today)."""
        return [copy for _, copy in self._found(source, path)]

    def latest(self, source: str, path: str) -> StagedCopy | None:
        """The newest staged copy (read last-first, so a stage of a new fetch lists but reads only one file)."""
        return next((copy for _, copy in self._found(source, path, newest_first=True)), None)

    def _found(self, source: str, path: str, newest_first: bool = False):
        path_parts(source)
        stamps = sorted(((t, n) for n in self.store.folders(source) if (t := _parse_stamp(n))), reverse=newest_first)
        for fetched_at, name in stamps:
            data = self.store.get(f"{source}/{name}/{path}")
            if data is not None:
                yield fetched_at, StagedCopy(source, fetched_at, path, data)
