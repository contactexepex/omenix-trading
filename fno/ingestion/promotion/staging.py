"""The Staging area (docs/PIPELINE_DESIGN.md): where every fetch lands before anything trusts it. A fetcher writes
here and nowhere else; only the promotion gate turns a staged file into a record.

Layout `<source>/<archive path>/<fetch time>`, e.g. `nse/nse/derivatives/participant-oi/2026/10/f.csv/20261026T153000Z`
(the archive path becomes a folder, as a revision's path does). All copies of one file are in one folder, so one
listing finds them and a lookup costs one listing plus one read per copy however many files are staged. Every fetch is
a new write-once object (the Drive store cannot overwrite a raw file); a newer fetch is a new copy beside the old one,
and the source and the fetch time are in the path. The fetch time is UTC `YYYYMMDDTHHMMSSZ` (sorts as time). Staging
holds raw, unchecked bytes: garbage may land here and is rejected by the gate.
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
        """Saves one fetch; False (nothing written) when the newest staged copy of this file already has these bytes
        (an older copy with the same bytes does not count: a file that changed and changed back is staged again)."""
        latest = self.latest(source, path)
        if latest and latest.data == data:
            return False
        self.store.put(self._name(source, path, stamp_of(fetched_at)), data)
        return True

    def copies(self, source: str, path: str) -> list[StagedCopy]:
        """The staged copies of an archive path from one source, earliest fetch first: the order the gate promotes in
        (the first passing copy becomes the record, as the first archived copy does today)."""
        return list(self._found(source, path, newest_first=False))

    def latest(self, source: str, path: str) -> StagedCopy | None:
        """The newest staged copy (one listing, one read)."""
        return next(self._found(source, path, newest_first=True), None)

    def _found(self, source: str, path: str, newest_first: bool):
        stamps = sorted(((t, n) for n in self.store.checksums(self._name(source, path)) if (t := _parse_stamp(n))),
                        reverse=newest_first)  # fmt: skip
        for fetched_at, name in stamps:
            data = self.store.get(self._name(source, path, name))
            if data is not None:
                yield StagedCopy(source, fetched_at, path, data)

    def children(self, source: str, folder: str = "") -> list[str]:
        """The folder names directly under a source (or a folder in it): which feeds or days hold staged files."""
        return self.store.folders(self._name(source, folder) if folder else source)

    @staticmethod
    def _name(source: str, path: str, stamp: str | None = None) -> str:
        path_parts(source)
        return f"{source}/{path}" if stamp is None else f"{source}/{path}/{stamp}"
