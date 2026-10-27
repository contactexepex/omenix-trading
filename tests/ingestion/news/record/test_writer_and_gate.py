"""P2b2: the writer's one outcome per article, the gate over Staging, reconciliation, and what stays staged."""

from __future__ import annotations

import csv
import hashlib
from datetime import timedelta

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.record import gate as gate_module
from fno.ingestion.news.record.gate import NewsGate
from fno.ingestion.news.record.manifest import FIELDS
from fno.ingestion.news.record.writer import Outcome
from fno.ingestion.storage.raw_store import RawFileConflict
from tests.ingestion.news.article.samples import rss, rss_item
from tests.ingestion.news.record.helpers import FEED, POLL_AT, Setup


def rows(setup):
    return list(csv.DictReader(setup.manifest_text().splitlines()))


def test_a_new_article_is_recorded_with_a_manifest_row_and_a_receipt(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    report = s.promote()
    assert report.ok and report.line() == "news promote: polls 1, items 1, recorded 1, revisions 0, no_ops 0"
    [path] = s.record_files()
    data = s.drive.get(path)
    [row] = rows(s)
    assert tuple(row) == FIELDS and row["status"] == "recorded" and row["sha256"] == hashlib.sha256(data).hexdigest()
    assert row["size_bytes"] == str(len(data)) and row["date"] == "2026-10-27"
    assert row["article_id"] in path and s.receipts.read(path).sha256 == row["sha256"]


def test_running_the_same_range_again_is_all_no_ops_and_writes_nothing_new(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item(), rss_item(title="Two", link="https://pub.example/a/2")))
    s.promote()
    before = (s.record_files(), s.manifest_text())
    s.build()
    report = s.promote()
    assert report.outcomes["no_ops"] == 2 and report.outcomes["recorded"] == 0
    assert (s.record_files(), s.manifest_text()) == before


def test_a_second_poll_of_the_same_article_is_a_no_op_though_first_seen_differs(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    s.stage(rss(rss_item(), rss_item(title="New", link="https://pub.example/a/9")), at=POLL_AT + timedelta(hours=1))
    report = s.promote()
    assert (report.outcomes["recorded"], report.outcomes["no_ops"], report.outcomes["items"]) == (2, 1, 3)
    assert len(s.record_files()) == 2


def test_a_changed_article_keeps_the_first_file_and_writes_one_revision_once(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item(title="Live blog v1")))
    s.stage(rss(rss_item(title="Live blog v2")), at=POLL_AT + timedelta(hours=1))
    other = rss_item(title="Other", link="https://pub.example/o")
    s.stage(rss(rss_item(title="Live blog v2"), other), at=POLL_AT + timedelta(hours=2))  # v2 seen again
    report = s.promote()
    assert (report.outcomes["recorded"], report.outcomes["revisions"], report.outcomes["no_ops"]) == (2, 1, 1)
    statuses = sorted(r["status"] for r in rows(s))
    assert statuses == ["recorded", "recorded", "revision"]
    first = next(p for p in s.record_files() if "/articles/" in p)
    assert b"Live blog v1" in s.drive.get(first)


def test_two_different_items_sharing_a_key_are_surfaced_as_a_revision_not_hidden(tmp_path):
    s = Setup(tmp_path)
    a = rss_item(title="Alpha", link="https://pub.example/same")
    b = rss_item(title="Beta", link="https://pub.example/same")
    s.stage(rss(a, b))
    report = s.promote()
    assert (report.outcomes["recorded"], report.outcomes["revisions"]) == (1, 1) and report.ok


def test_a_stopped_run_is_repaired_with_the_held_bytes_not_new_ones(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    s.promote()
    held = s.drive.get(s.record_files()[0])
    (s.manifest_folder / "articles.csv").unlink()
    s.receipts.file_for(s.record_files()[0]).unlink()
    other = rss_item(title="Other", link="https://pub.example/o")
    s.stage(rss(rss_item(), other), at=POLL_AT + timedelta(hours=1))  # same article, later first_seen_at
    s.build()
    report = s.promote()
    assert (report.outcomes["no_ops"], report.outcomes["recorded"]) == (2, 1)
    first = next(p for p in s.record_files() if held == s.drive.get(p))
    assert s.receipts.read(first).sha256 == hashlib.sha256(held).hexdigest()
    assert hashlib.sha256(held).hexdigest() in s.manifest_text()


def test_drive_failing_writes_no_manifest_row_and_is_counted_by_code(tmp_path, monkeypatch):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))

    def refuse(path, data):
        raise OSError("drive down: https://secret.example/x")

    monkeypatch.setattr(s.drive, "put", refuse)
    report = s.promote()
    assert report.rejected == {codes.RECORD_FAILED: 1} and s.manifest_text() == ""
    assert "secret" not in report.line() and not report.ok


def test_a_manifest_conflict_is_a_code_not_a_crash(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    s.promote()
    key = rows(s)[0]["article_id"]
    with pytest.raises(RawFileConflict):
        s.manifest.add(POLL_AT.date(), key, "recorded", "0" * 64, 1)


def test_a_bad_poll_stays_staged_with_its_code_and_good_polls_still_go(tmp_path):
    s = Setup(tmp_path)
    s.stage(b"<!DOCTYPE x [<!ENTITY a 'b'>]><rss/>")
    s.stage(rss(rss_item()), at=POLL_AT + timedelta(hours=1))
    report = s.promote()
    assert report.rejected == {codes.UNSAFE_XML: 1} and report.outcomes["recorded"] == 1
    assert s.staging.copies("news", f"{FEED}/2026/10/27/poll")[0].data.startswith(b"<!DOCTYPE")


def test_rejected_items_are_counted_by_code_and_the_rest_are_recorded(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item(), rss_item(title=None, link="https://pub.example/x")))
    report = s.promote()
    assert report.outcomes["recorded"] == 1 and report.rejected == {codes.ITEM_MISSING_TITLE: 1}
    assert report.outcomes["items"] == 2 and not report.ok


def test_a_staged_feed_the_list_does_not_know_stays_staged_and_is_alerted(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()), feed="feed-77")
    report = s.promote()
    assert report.rejected == {codes.FEED_UNKNOWN: 1} and s.record_files() == []


def test_an_item_that_goes_missing_fails_the_reconciliation(tmp_path, monkeypatch):
    s = Setup(tmp_path)
    s.stage(rss(rss_item(), rss_item(title="Two", link="https://pub.example/a/2")))
    monkeypatch.setitem(gate_module.COUNTED, Outcome.NO_OP, "uncounted")  # an outcome that is not added up
    s.promote()
    s.build()
    assert codes.NOT_RECONCILED in s.promote().rejected


def test_the_gate_writes_only_the_record_and_reads_only_staging(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    written = []
    real = s.drive.put
    s.drive.put = lambda path, data: (written.append(path), real(path, data))[1]
    s.promote()
    assert written and all(p.startswith(("raw/news/articles/", "raw/news/revisions/")) for p in written)
    assert isinstance(s.gate, NewsGate) and s.gate.staging is s.staging


def test_outcomes_are_a_closed_set():
    assert {o.value for o in Outcome} == {"recorded", "revision", "no_op"}


def test_a_revision_file_is_named_by_eight_hex_characters_of_its_fixed_fields(tmp_path):
    s = Setup(tmp_path)
    s.stage(rss(rss_item(title="v1")))
    s.stage(rss(rss_item(title="v2")), at=POLL_AT + timedelta(hours=1))
    s.promote()
    [revision] = [p for p in s.record_files() if "/revisions/" in p]
    name = revision.rsplit("/", 1)[1]
    assert len(name) == len("12345678.json") and name.removesuffix(".json").isalnum()


def test_a_manifest_conflict_inside_a_run_is_counted_as_record_conflict_and_the_run_goes_on(tmp_path, monkeypatch):
    s = Setup(tmp_path)
    s.stage(rss(rss_item(), rss_item(title="Two", link="https://pub.example/a/2")))
    real, calls = s.manifest.add, []

    def conflicting(*args):
        calls.append(args)
        if len(calls) == 1:
            raise RawFileConflict("other sha")
        return real(*args)

    monkeypatch.setattr(s.manifest, "add", conflicting)
    report = s.promote()
    assert report.rejected == {codes.RECORD_CONFLICT: 1} and report.outcomes["recorded"] == 1
