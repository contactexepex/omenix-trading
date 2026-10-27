"""Story S1, owner's choice (b): a staged news poll is removed only when every article in it is already in the Record.
Built on the real promotion gate and writer (tests/ingestion/news/record/helpers.py): "promoted" is the real state."""

from __future__ import annotations

from datetime import timedelta

import pytest

from fno.ingestion.news.fetcher import SOURCE
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.planner import ArticlePlanner
from fno.ingestion.staging_cleanup.cleanup import StagingCleanup
from fno.ingestion.staging_cleanup.news_proof import NewsPollProof
from fno.ingestion.storage.raw_store import AreaStore
from tests.ingestion.news.article.samples import rss, rss_item
from tests.ingestion.news.record.helpers import FEED, POLL_AT, Setup
from tests.ingestion.staging_cleanup.test_cleanup import Trash

LATER = POLL_AT + timedelta(days=9)  # the cleanup runs 9 days after the poll


def proof_for(setup: Setup, kinds=None) -> NewsPollProof:
    manifest = NewsManifest(setup.manifest_folder)
    return NewsPollProof(
        kinds if kinds is not None else setup.kinds, ArticlePlanner(AreaStore(setup.drive, "raw")), manifest
    )


def staged(setup: Setup):
    path = f"{FEED}/{POLL_AT:%Y/%m/%d}/poll"
    return setup.staging.read(SOURCE, path, setup.staging.stamps(SOURCE, path)[0][1])


def cleanup(setup: Setup, trash, proof=None) -> StagingCleanup:
    return StagingCleanup(setup.staging, {SOURCE: proof or proof_for(setup)}, trash, clock=lambda: LATER)


def test_a_poll_whose_articles_are_all_in_the_record_with_manifest_rows_is_promoted_and_trashed(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item(), rss_item(title="Second story", link="https://example.com/second")))
    assert s.promote().ok
    trash = Trash()
    report = cleanup(s, trash).run([SOURCE])
    assert report.counts["trashed"] == 1 and len(trash.calls) == 1 and trash.calls[0][0] == SOURCE


def test_a_poll_that_was_never_promoted_is_kept(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    trash = Trash()
    report = cleanup(s, trash).run([SOURCE])
    assert trash.calls == [] and report.counts["unproven"] == 1


def test_one_missing_article_keeps_the_whole_poll(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    s.promote()
    s.stage(
        rss(rss_item(), rss_item(title="Fresh story", link="https://example.com/fresh")),
        at=POLL_AT + timedelta(hours=1),
    )
    trash = Trash()
    cleanup(s, trash).run([SOURCE])
    assert [c[2] for c in trash.calls] == [
        "20261027T030000Z"
    ]  # the first poll goes; the second still has an unrecorded article


def test_a_poll_with_a_rejected_item_is_kept_even_if_the_rest_is_recorded(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item(), "<item><description>no title and no link</description></item>"))
    s.promote()
    trash = Trash()
    report = cleanup(s, trash).run([SOURCE])
    assert trash.calls == [] and report.counts["unproven"] == 1


def test_a_poll_of_a_feed_that_is_not_in_the_feed_list_is_kept(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    s.promote()
    trash = Trash()
    cleanup(s, trash, proof_for(s, kinds={})).run([SOURCE])
    assert trash.calls == []


def test_an_article_in_the_record_with_no_manifest_row_keeps_the_poll(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    s.promote()
    (s.manifest_folder / "articles.csv").write_text("")  # the manifest of the checkout lost its rows
    trash = Trash()
    cleanup(s, trash).run([SOURCE])
    assert trash.calls == []


def test_a_changed_version_counts_as_held_only_through_its_revision_file(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item(title="Story v1")))
    s.stage(rss(rss_item(title="Story v2")), at=POLL_AT + timedelta(hours=1))
    s.promote()  # the second poll is a REVISION of the same key
    trash = Trash()
    report = cleanup(s, trash).run([SOURCE])
    assert report.counts["trashed"] == 2 and len(trash.calls) == 2


def test_a_record_that_cannot_be_read_keeps_the_poll(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    s.promote()

    class Down(AreaStore):
        def get(self, path):
            raise OSError("Drive down")

    proof = NewsPollProof(s.kinds, ArticlePlanner(Down(s.drive, "raw")), NewsManifest(s.manifest_folder))
    trash = Trash()
    cleanup(s, trash, proof).run([SOURCE])
    assert trash.calls == []


def test_a_poll_younger_than_seven_days_is_kept_even_when_promoted(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    s.promote()
    trash = Trash()
    young = StagingCleanup(s.staging, {SOURCE: proof_for(s)}, trash, clock=lambda: POLL_AT + timedelta(days=3))
    assert young.run([SOURCE]).counts["young"] == 1 and trash.calls == []


@pytest.mark.parametrize("path", ["feed-01/2026/10/27", "feed-01/2026/10/27/other"])
def test_only_a_poll_folder_is_ever_judged(tmp_path, path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    s.promote()
    s.staging.stage(SOURCE, path, rss(rss_item()), POLL_AT)  # genuine feed bytes, all held, but not in a poll folder
    trash = Trash()
    cleanup(s, trash).run([SOURCE])
    assert trash.calls and all(call[1].endswith("/poll") for call in trash.calls)
