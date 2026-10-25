"""A raw-file source that publishes nothing: reads of NSE's archived files stay reads of what is already stored."""

from ...storage.raw_source import RawFileSource


class StoredFilesOnly(RawFileSource):
    """The library's source when a file must already be archived: it publishes nothing, so a missing file stays
    missing and no request ever goes to NSE (story section 2: no new NSE read)."""

    name = "stored files only"

    def fetch(self, path: str) -> bytes | None:
        return None
