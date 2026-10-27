"""NP2a: format 1 files already in the Record are not rewritten as "revisions" when their article is seen again, and a
changed redirect link never makes a revision."""

from __future__ import annotations

import json

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.record.planner import ArticlePlanner, Outcome, article_path, same_version
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore

BASE = {
    "key": "ab" * 32, "kind": "wrapper", "source": "S", "title": "T", "summary": "s", "canonical_url": "",
    "published_at": "2026-10-27T02:00:00+00:00", "time_source": "feed", "first_seen_at": "2026-10-27T03:00:00+00:00",
}  # fmt: skip


def v1_bytes(**changes):
    return json.dumps({"format": 1, **BASE, **changes}).encode()


def article(**changes) -> Article:
    return Article(
        **{**BASE, "source_domain": "outlet.example", "wrapper_link": "https://wrap.example/a?x=1", **changes}
    )


def planner_holding(tmp_path, data: bytes) -> ArticlePlanner:
    record = AreaStore(LocalFolderStore(tmp_path / "drive"), "raw")
    record.put(article_path(BASE["key"]), data)
    return ArticlePlanner(record)


def test_a_format_1_file_and_the_same_article_as_format_2_are_a_no_op_not_a_revision(tmp_path):
    assert planner_holding(tmp_path, v1_bytes()).plan(article()).outcome is Outcome.NO_OP


def test_a_format_1_file_and_a_format_2_article_that_differs_in_a_shared_field_is_a_revision(tmp_path):
    assert planner_holding(tmp_path, v1_bytes()).plan(article(title="T (corrected)")).outcome is Outcome.REVISION


def test_two_format_2_files_that_differ_in_the_source_domain_are_a_revision(tmp_path):
    held = article(source_domain="").to_bytes()
    assert planner_holding(tmp_path, held).plan(article()).outcome is Outcome.REVISION


def test_the_same_format_2_article_is_a_no_op_and_first_seen_at_is_never_compared(tmp_path):
    plan = planner_holding(tmp_path, article().to_bytes()).plan(article(first_seen_at="2026-10-28T09:00:00+00:00"))
    assert plan.outcome is Outcome.NO_OP


def test_a_changed_redirect_link_is_not_a_new_version_so_a_moving_token_never_makes_revisions(tmp_path):
    plan = planner_holding(tmp_path, article().to_bytes()).plan(article(wrapper_link="https://wrap.example/b?x=2"))
    assert plan.outcome is Outcome.NO_OP


def test_a_damaged_held_file_or_files_sharing_no_field_are_never_the_same_version():
    assert not same_version(b"garbage", article().to_bytes()) and not same_version(article().to_bytes(), b"[1]")
    assert not same_version(b"{}", article().to_bytes())  # nothing in common says nothing about sameness
