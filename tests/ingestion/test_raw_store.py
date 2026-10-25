"""The write-once raw-file store (``fno/ingestion/storage/raw_store.py``) against a real ``tmp_path`` dir."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fno.ingestion.storage.raw_store import (
    AreaStore,
    LocalFolderStore,
    RawFileConflict,
    path_parts,
)

PATH = "raw/nse/derivatives/fo-bhavcopy/2026/10/file.csv.zip"


def test_path_parts_valid_and_invalid() -> None:
    assert path_parts("a/b/c.csv") == ["a", "b", "c.csv"]
    for bad in ("", "/abs/path", "a/../b", "a//b", "a/./b"):
        with pytest.raises(ValueError):
            path_parts(bad)


def test_put_then_get_round_trip(tmp_path: Path) -> None:
    store = LocalFolderStore(tmp_path)
    assert store.get(PATH) is None
    store.put(PATH, b"hello world")
    assert store.get(PATH) == b"hello world"


def test_same_bytes_again_is_noop(tmp_path: Path) -> None:
    store = LocalFolderStore(tmp_path)
    store.put(PATH, b"data")
    store.put(PATH, b"data")  # no error
    assert store.get(PATH) == b"data"


def test_different_bytes_refused(tmp_path: Path) -> None:
    store = LocalFolderStore(tmp_path)
    store.put(PATH, b"original")
    with pytest.raises(RawFileConflict):
        store.put(PATH, b"changed")
    assert store.get(PATH) == b"original"  # original untouched


def test_no_partial_file_left_under_real_name(tmp_path: Path) -> None:
    store = LocalFolderStore(tmp_path)
    store.put("raw/a/b/f.bin", b"x")
    # The atomic write uses a ".part" temp name that must not survive.
    assert not list(tmp_path.rglob("*.part"))


def test_checksums_and_folders(tmp_path: Path) -> None:
    store = LocalFolderStore(tmp_path)
    store.put("raw/d/2026/one.csv", b"one")
    store.put("raw/d/2026/two.csv", b"two")
    store.put("raw/d/2027/three.csv", b"three")
    sums = store.checksums("raw/d/2026")
    assert set(sums) == {"one.csv", "two.csv"}
    assert sums["one.csv"] == hashlib.md5(b"one").hexdigest()  # noqa: S324 - matches Drive's checksum
    assert store.folders("raw/d") == ["2026", "2027"]
    assert store.checksums("raw/missing") == {}
    assert store.folders("raw/missing") == []


def test_area_store_prefixes_paths(tmp_path: Path) -> None:
    base = LocalFolderStore(tmp_path)
    area = AreaStore(base, "raw")
    area.put("nse/f.csv", b"bytes")
    assert area.get("nse/f.csv") == b"bytes"
    assert base.get("raw/nse/f.csv") == b"bytes"  # the area is a real sub-folder
    assert area.name == base.name
