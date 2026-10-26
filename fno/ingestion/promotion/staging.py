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
        latest = self.copies(source, path, limit=1)
        if latest and latest[0].data == data:
            return False
        self.store.put(f"{source}/{stamp_of(fetched_at)}/{path}", data)
        return True

    def copies(self, source: str, path: str, limit: int | None = None) -> list[StagedCopy]:
        """The staged copies of an archive path from one source, newest fetch first (at most `limit`)."""
        path_parts(source)
        stamps = sorted(((t, n) for n in self.store.folders(source) if (t := _parse_stamp(n))), reverse=True)
        found: list[StagedCopy] = []
        for fetched_at, name in stamps:
            data = self.store.get(f"{source}/{name}/{path}")
            if data is not None:
                found.append(StagedCopy(source, fetched_at, path, data))
                if limit is not None and len(found) >= limit:
                    break
        return found
