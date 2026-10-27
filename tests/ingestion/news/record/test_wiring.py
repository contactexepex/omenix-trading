"""P2b2: the composition root itself, on a recording fake Drive (judge 48 S1), and the feed kinds it reads (S2)."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FEEDS_FOLDER, FeedListError, PrivateFeedLists
from fno.ingestion.news.record import wiring
from fno.ingestion.storage.batch_receipts import BatchReceiptWriter
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore
from fno.ingestion.storage.receipts import ReceiptFolder
from tests.ingestion.news.article.samples import rss, rss_item
from tests.ingestion.news.fakes import SALT
from tests.ingestion.news.record.helpers import POLL_AT

DAY = POLL_AT.date()


class RecordingDrive(LocalFolderStore):
    def __init__(self, folder):
        super().__init__(folder)
        self.writes, self.reads = [], []

    def put(self, path, data):
        self.writes.append(path)
        super().put(path, data)

    def get(self, path):
        self.reads.append(path)
        return super().get(path)


def feed_list(version, drive, *feeds):
    entries = [
        {"id": i, "url": f"https://h{n}.example/rss", **({"kind": k} if k else {})} for n, (i, k) in enumerate(feeds)
    ]
    drive.put(f"config/{FEEDS_FOLDER}/feeds-v{version}.json", json.dumps({"salt": SALT, "feeds": entries}).encode())


@pytest.fixture
def world(tmp_path, monkeypatch):
    drive = RecordingDrive(tmp_path / "drive")
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env=None: drive)
    monkeypatch.setattr(
        wiring,
        "batch_receipt_writer",
        lambda run_id: BatchReceiptWriter(ReceiptFolder(tmp_path / "repo" / "receipts"), run_id),
    )
    monkeypatch.setattr(wiring, "POLL_LOG_FOLDER", tmp_path / "repo" / "manifests")
    return drive


def stage(drive, feed, data, at=POLL_AT):
    drive.put(f"staging/news/{feed}/{at:%Y/%m/%d}/poll/{at:%Y%m%dT%H%M%SZ}", data)


def test_the_wired_gate_writes_only_the_record_areas_and_reads_only_staging_config_and_record(world):
    feed_list(1, world, ("feed-01", None))
    stage(world, "feed-01", rss(rss_item(title="v1")))
    stage(world, "feed-01", rss(rss_item(title="v2")), POLL_AT + timedelta(hours=1))
    world.writes.clear()
    report = wiring.build_news_promotion().promote(DAY, DAY)
    assert report.ok and report.outcomes["recorded"] == 1 and report.outcomes["revisions"] == 1
    assert world.writes and all(p.startswith(("raw/news/articles/", "raw/news/revisions/")) for p in world.writes)
    assert all(p.startswith(("staging/news/", "config/feeds/", "raw/news/")) for p in world.reads)
    assert any(p.startswith("staging/news/") for p in world.reads)
    again = wiring.build_news_promotion().promote(DAY, DAY)  # a new process reads the Record back: all no-ops
    assert (again.outcomes["recorded"], again.outcomes["revisions"], again.outcomes["no_ops"]) == (0, 0, 2)


def test_the_wired_gate_receipts_every_record_file_in_one_batch_file_for_the_run(world, tmp_path):
    feed_list(1, world, ("feed-01", None))
    stage(world, "feed-01", rss(rss_item(title="v1")))
    stage(world, "feed-01", rss(rss_item(title="v2")), POLL_AT + timedelta(hours=1))
    world.writes.clear()
    wiring.build_news_promotion().promote(DAY, DAY)
    receipts = tmp_path / "repo" / "receipts"
    assert len(list((receipts / "_batches").rglob("*.tsv"))) == 1 and not list(receipts.rglob("*.sha256"))
    folder = ReceiptFolder(receipts)
    assert sorted(r.path for r in folder.under("raw/news")) == sorted(
        f"raw/{p.removeprefix('raw/')}" for p in world.writes
    )


def test_a_feed_retired_from_the_newest_list_still_promotes_its_old_polls(world):
    feed_list(1, world, ("feed-01", None), ("feed-02", "wrapper"))
    feed_list(2, world, ("feed-01", None))
    stage(world, "feed-02", rss(rss_item(title="old")))
    report = wiring.build_news_promotion().promote(DAY, DAY)
    assert report.ok and report.outcomes["recorded"] == 1
    assert wiring.build_news_promotion().promote(DAY + timedelta(days=5), DAY + timedelta(days=5)).ok


def test_a_changed_kind_for_one_feed_id_stops_the_run_with_a_fixed_code(world):
    feed_list(1, world, ("feed-01", None))
    feed_list(2, world, ("feed-01", "wrapper"))
    with pytest.raises(FeedListError, match=codes.FEED_KIND_CHANGED):
        wiring.build_news_promotion()


def test_an_unreadable_old_version_is_skipped_and_no_version_at_all_is_a_missing_list(world):
    with pytest.raises(FeedListError, match=codes.FEED_LIST_MISSING):
        PrivateFeedLists(AreaStore(world, "config")).kinds_ever_listed()
    world.put(f"config/{FEEDS_FOLDER}/feeds-v1.json", b"not json")
    feed_list(2, world, ("feed-01", None))
    assert PrivateFeedLists(AreaStore(world, "config")).kinds_ever_listed() == {"feed-01": "publisher"}
