"""Each write-once layer refuses on its own, not only behind another one (P5 follow-up: contract rows W2 and W4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from fno.ingestion.storage.raw_store import LocalFolderStore, RawFileConflict
from fno.ingestion.storage.receipts import Receipt, ReceiptFolder

PATH = "data/x/f.csv"


def _receipt(sha256: str, written_at: str = "2026-10-27T00:00:00+00:00") -> Receipt:
    return Receipt(PATH, sha256, 3, written_at, "test", "run-1")


def test_a_write_that_dies_midway_leaves_nothing_under_the_real_name(tmp_path: Path, monkeypatch) -> None:
    def half_write_then_die(self: Path, data: bytes) -> int:
        with self.open("wb") as handle:
            handle.write(data[:1])
        raise OSError("disk went away")

    monkeypatch.setattr(Path, "write_bytes", half_write_then_die)
    store = LocalFolderStore(tmp_path)
    with pytest.raises(OSError):
        store.put("raw/a/f.bin", b"whole file")
    assert not (tmp_path / "raw/a/f.bin").exists()


def test_the_receipt_layer_refuses_a_different_digest_by_itself(tmp_path: Path) -> None:
    receipts = ReceiptFolder(tmp_path)
    receipts.write(_receipt("a" * 64))
    with pytest.raises(RawFileConflict):
        receipts.write(_receipt("b" * 64))
    assert receipts.read(PATH).sha256 == "a" * 64


def test_the_receipt_layer_keeps_the_first_receipt_for_the_same_digest(tmp_path: Path) -> None:
    receipts = ReceiptFolder(tmp_path)
    first = receipts.write(_receipt("a" * 64, "2026-10-27T00:00:00+00:00"))
    again = receipts.write(_receipt("a" * 64, "2026-10-28T00:00:00+00:00"))
    assert again == first
    assert receipts.read(PATH).written_at == "2026-10-27T00:00:00+00:00"
