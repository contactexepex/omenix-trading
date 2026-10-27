"""NP2d: the gate learns which recorded articles are Google News items, and changes nothing else."""

from __future__ import annotations

import hashlib

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.article.keys import PUBLISHER, WRAPPER
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.wrapper_index import WRAPPERS_FILE
from fno.ingestion.news.record.writer import ArticleWriter
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.row_log import TableFileBroken
from tests.ingestion.news.article.samples import rss, rss_item
from tests.ingestion.news.record.helpers import POLL_AT, Setup

WRAP_FEED, PUB_FEED = "feed-01", "feed-02"


def wrapper_item(n: int, link: bool = True) -> str:
    return rss_item(
        title=f"Zzwrap {n}", link=f"https://wrap.svc.example/rss/articles/CBMi{n:04d}?oc=5" if link else "",
        guid=f"g-{n}", source="Outlet", source_url="https://outlet.example",
    )  # fmt: skip


def world(tmp_path) -> Setup:
    return Setup(tmp_path, kinds={WRAP_FEED: WRAPPER, PUB_FEED: PUBLISHER})


def index_rows(setup: Setup) -> list[str]:
    path = setup.manifest_folder / WRAPPERS_FILE
    return path.read_text().splitlines()[1:] if path.exists() else []


def test_a_recorded_wrapper_article_with_a_link_gets_one_row_and_nothing_else_does(tmp_path):
    setup = world(tmp_path)
    setup.stage(rss(wrapper_item(1), wrapper_item(2)), feed=WRAP_FEED)
    setup.stage(rss(rss_item(title="Zzpub", link="https://pub.example/a/1")), feed=PUB_FEED)
    setup.promote()
    rows = index_rows(setup)
    assert len(rows) == 2 and all(",recorded," in r for r in rows)
    index = NewsManifest(setup.manifest_folder, WRAPPERS_FILE)
    articles = NewsManifest(setup.manifest_folder)
    assert set(index.recorded) < set(articles.recorded) and len(articles.recorded) == 3


def test_a_wrapper_item_without_a_usable_link_is_not_indexed(tmp_path):
    setup = world(tmp_path)
    setup.stage(rss(wrapper_item(1, link=False)), feed=WRAP_FEED)
    report = setup.promote()
    assert report.ok and index_rows(setup) == [] and len(NewsManifest(setup.manifest_folder).recorded) == 1


def test_the_row_carries_the_sha_of_the_article_file_the_record_holds(tmp_path):
    setup = world(tmp_path)
    setup.stage(rss(wrapper_item(1)), feed=WRAP_FEED)
    setup.promote()
    (path,) = (setup.drive.folder / "raw/news/articles").rglob("*.json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() in index_rows(setup)[0]


def test_promoting_the_same_poll_again_adds_no_second_row(tmp_path):
    setup = world(tmp_path)
    setup.stage(rss(wrapper_item(1)), feed=WRAP_FEED)
    setup.promote()
    setup.build()
    setup.promote()
    assert len(index_rows(setup)) == 1


def test_a_missing_row_is_repaired_by_promoting_the_poll_again(tmp_path):
    """A run killed between the article row and the index row: the next promote of the same poll adds it."""
    setup = world(tmp_path)
    setup.stage(rss(wrapper_item(1)), feed=WRAP_FEED)
    setup.promote()
    (setup.manifest_folder / WRAPPERS_FILE).unlink()
    setup.build()
    report = setup.promote()
    assert report.outcomes["no_ops"] == 1 and len(index_rows(setup)) == 1


def test_a_revision_adds_no_row_and_the_first_rows_stay(tmp_path):
    setup = world(tmp_path)
    setup.stage(rss(wrapper_item(1)), feed=WRAP_FEED)
    setup.promote()
    changed = wrapper_item(1).replace("Zzwrap 1", "Zzwrap 1 corrected")
    setup.stage(rss(changed), feed=WRAP_FEED, at=POLL_AT.replace(hour=5))
    setup.build()
    report = setup.promote()
    assert report.outcomes["revisions"] == 1 and len(index_rows(setup)) == 1


def test_the_gate_decides_exactly_as_before_the_index_existed(tmp_path):
    with_index, without = world(tmp_path / "a"), world(tmp_path / "b")
    without.writer = ArticleWriter(AreaStore(without.drive, "raw"), without.writer.store, without.manifest)
    without.gate.writer = without.writer
    lines = []
    for setup in (with_index, without):
        setup.stage(rss(wrapper_item(1), wrapper_item(2, link=False)), feed=WRAP_FEED)
        setup.stage(rss(rss_item(title="Zzpub", link="https://pub.example/a/1")), feed=PUB_FEED)
        lines.append(setup.promote().line())
    assert lines[0] == lines[1] and "recorded 3" in lines[0]
    assert with_index.record_files() == without.record_files()
    assert with_index.manifest_text() == without.manifest_text()


def test_a_torn_index_stops_the_promotion_before_anything_is_written(tmp_path):
    setup = world(tmp_path)
    setup.stage(rss(wrapper_item(1)), feed=WRAP_FEED)
    (setup.manifest_folder).mkdir(parents=True, exist_ok=True)
    row = "2026-10-27," + "a" * 64 + ",recorded," + "b" * 64 + ",10"
    (setup.manifest_folder / WRAPPERS_FILE).write_text("date,article_id,status,sha256,size_bytes\n" + row)
    setup.build()
    with pytest.raises(TableFileBroken):
        setup.promote()
    assert setup.record_files() == []


def test_a_row_of_the_index_that_is_not_whole_is_reported_and_not_ignored(tmp_path):
    setup = world(tmp_path)
    setup.stage(rss(wrapper_item(1)), feed=WRAP_FEED)
    (setup.manifest_folder).mkdir(parents=True, exist_ok=True)
    (setup.manifest_folder / WRAPPERS_FILE).write_text("date,article_id,status,sha256,size_bytes\nnot,a,whole,row,x\n")
    setup.build()
    assert codes.MANIFEST_ROW_SKIPPED in setup.promote().rejected
