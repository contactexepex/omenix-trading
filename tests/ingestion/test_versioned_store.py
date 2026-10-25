"""The point-in-time versioned reader (``fno/ingestion/storage/versioned_store.py``): it returns the right revision
for an ``as_of`` time, the newest for publishing, and reports a damaged stored copy. No network; stores are on disk."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pytest

from fno.ingestion.storage.raw_store import LocalFolderStore, ReadOnlyStoreError, StoredCopyDamaged
from fno.ingestion.storage.revisions import Revision
from fno.ingestion.storage.versioned_store import VersionedRawStore
from fno.shared.models import IST

PATH = "nse/indices/index-close/2026/10/ind_close_all_12102026.csv"
T1 = datetime(2026, 10, 12, 16, 0, tzinfo=IST)
T2 = datetime(2026, 10, 12, 23, 20, tzinfo=IST)  # NSE rewrote the file later that night


class _FakeIndex:
    def __init__(self, revisions: list[Revision]):
        self._revisions = revisions

    def for_path(self, path: str) -> list[Revision]:
        return list(self._revisions)


def _revision(data: bytes, available_from: datetime) -> Revision:
    from datetime import date

    return Revision(
        day=date(2026, 10, 12),
        path=PATH,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        available_from=available_from,
        last_modified=available_from,
        found_at=available_from,
    )


def _wire(tmp_path: Path):
    raw = LocalFolderStore(tmp_path / "raw")
    revisions = LocalFolderStore(tmp_path / "revisions")
    raw.put(PATH, b"v0-original")
    rev1, rev2 = _revision(b"v1-rewrite", T1), _revision(b"v2-rewrite", T2)
    revisions.put(rev1.revision_path, b"v1-rewrite")
    revisions.put(rev2.revision_path, b"v2-rewrite")
    index = _FakeIndex([rev1, rev2])
    return raw, revisions, index


def test_latest_returns_newest_revision(tmp_path: Path) -> None:
    raw, revisions, index = _wire(tmp_path)
    store = VersionedRawStore(raw, revisions, index, as_of=None)
    assert store.get(PATH) == b"v2-rewrite"


def test_point_in_time_picks_the_version_available_then(tmp_path: Path) -> None:
    raw, revisions, index = _wire(tmp_path)
    between = datetime(2026, 10, 12, 18, 0, tzinfo=IST)
    assert VersionedRawStore(raw, revisions, index, as_of=between).get(PATH) == b"v1-rewrite"


def test_before_any_revision_returns_raw(tmp_path: Path) -> None:
    raw, revisions, index = _wire(tmp_path)
    before = datetime(2026, 10, 12, 15, 0, tzinfo=IST)
    assert VersionedRawStore(raw, revisions, index, as_of=before).get(PATH) == b"v0-original"


def test_no_revisions_returns_raw(tmp_path: Path) -> None:
    raw = LocalFolderStore(tmp_path / "raw")
    raw.put(PATH, b"only-raw")
    store = VersionedRawStore(raw, LocalFolderStore(tmp_path / "rev"), _FakeIndex([]), as_of=None)
    assert store.get(PATH) == b"only-raw"


def test_versioned_store_never_writes(tmp_path: Path) -> None:
    raw, revisions, index = _wire(tmp_path)
    with pytest.raises(ReadOnlyStoreError):
        VersionedRawStore(raw, revisions, index, as_of=None).put(PATH, b"x")


def test_damaged_stored_copy_is_reported(tmp_path: Path) -> None:
    raw = LocalFolderStore(tmp_path / "raw")
    revisions = LocalFolderStore(tmp_path / "revisions")
    raw.put(PATH, b"v0")
    rev = _revision(b"the-indexed-bytes", T1)
    revisions.put(rev.revision_path, b"different-bytes-than-indexed")  # hash will not match the receipt
    store = VersionedRawStore(raw, revisions, _FakeIndex([rev]), as_of=None)
    with pytest.raises(StoredCopyDamaged):
        store.get(PATH)
