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


# ---- judge 73 B1 and judge 74 F2: a file that is not whole is never "the same version" ------------------------------


def v2(**changes):
    return article(**changes).to_bytes()


def test_a_same_format_file_missing_a_key_is_not_the_same_version_as_a_whole_one():
    whole = json.loads(v2())
    for missing in ("title", "source_domain", "wrapper_link", "key"):
        partial = {k: v for k, v in whole.items() if k != missing}
        assert not same_version(json.dumps(partial).encode(), v2()) and not same_version(
            v2(), json.dumps(partial).encode()
        )


def test_a_file_with_an_unknown_extra_key_or_a_stub_is_not_the_same_version():
    assert not same_version(json.dumps({**json.loads(v2()), "surprise": 1}).encode(), v2())
    assert not same_version(json.dumps({"format": 2, "key": "k"}).encode(), v2())
    assert not same_version(json.dumps({"format": 1, "key": BASE["key"]}).encode(), v1_bytes())


def test_a_same_format_title_difference_is_not_hidden_by_a_missing_title():
    assert not same_version(
        json.dumps({k: v for k, v in json.loads(v2()).items() if k != "title"}).encode(), v2(title="Other")
    )


def test_a_format_must_be_an_integer_we_know_so_true_and_one_point_zero_and_three_are_refused():
    for bad in (True, 1.0, 3, "2", None):
        assert not same_version(json.dumps({**json.loads(v2()), "format": bad}).encode(), v2())
    for bad in (True, 1.0):  # equal to 1 in Python, with exactly format 1's keys: still not an integer format
        assert not same_version(json.dumps({"format": bad, **BASE}).encode(), v1_bytes())


def test_a_format_1_file_with_format_2_keys_and_a_format_2_file_without_them_are_not_ours():
    assert not same_version(
        json.dumps({"format": 1, **BASE, "source_domain": "x", "wrapper_link": ""}).encode(), v1_bytes()
    )
    without = {k: v for k, v in json.loads(v2()).items() if k not in ("source_domain", "wrapper_link")}
    assert not same_version(json.dumps(without).encode(), v2())


def test_the_field_sets_of_the_formats_match_the_article_so_a_new_field_needs_a_new_format():
    from dataclasses import fields

    from fno.ingestion.news.article.formats import FIELDS_OF

    assert FIELDS_OF[2] == {f.name for f in fields(Article)}


# --- judge 74 F1: a revision kept under one format is not written again under another ---


def test_a_revision_kept_in_format_1_is_not_written_again_when_the_same_version_is_seen_in_format_2(tmp_path):
    record = AreaStore(LocalFolderStore(tmp_path / "drive"), "raw")
    key = BASE["key"]
    record.put(article_path(key), v1_bytes(title="T1"))
    old_revision = f"news/revisions/{key[:2]}/{key}/d98f05bf.json"
    record.put(old_revision, v1_bytes(title="T2"))
    plan = ArticlePlanner(record).plan(article(title="T2"))
    assert plan.outcome is Outcome.NO_OP and plan.path == old_revision and plan.status == "revision"


def test_two_format_2_versions_that_differ_only_in_the_source_domain_get_two_revision_names(tmp_path):
    record = AreaStore(LocalFolderStore(tmp_path / "drive"), "raw")
    record.put(article_path(BASE["key"]), v2(title="T1"))
    first = ArticlePlanner(record).plan(article(title="T2", source_domain="a.example"))
    assert first.outcome is Outcome.REVISION
    record.put(first.path, article(title="T2", source_domain="a.example").to_bytes())
    second = ArticlePlanner(record).plan(article(title="T2", source_domain="b.example"))
    assert second.outcome is Outcome.REVISION and second.path != first.path


# --- judge 74 add.1: a listing that lags behind a revision written earlier in the run ---


class LaggingListing(AreaStore):
    """A store whose folder listing never shows files written in this run (a lagging Drive listing)."""

    def checksums(self, folder):
        return {}


def test_a_lagging_listing_gives_no_op_for_the_same_version_and_a_conflict_only_for_a_different_one(tmp_path):
    from fno.ingestion.storage.raw_store import RawFileConflict

    record = LaggingListing(LocalFolderStore(tmp_path / "drive"), "raw")
    record.put(article_path(BASE["key"]), v2(title="T1"))
    planner = ArticlePlanner(record)
    first = planner.plan(article(title="T2"))
    assert first.outcome is Outcome.REVISION
    planner.held[first.path] = article(title="T2").to_bytes()  # what ArticleWriter does after writing it
    again = planner.plan(article(title="T2"))  # the listing does not show it, the cache does
    assert again.outcome is Outcome.NO_OP and again.path == first.path
    planner.held[first.path] = article(title="T3").to_bytes()  # a different version under the same name
    import pytest

    with pytest.raises(RawFileConflict):
        planner.plan(article(title="T2"))
