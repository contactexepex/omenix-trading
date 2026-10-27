"""NP4b: the page-read pass over the Record, with a fake fetcher (no request is made anywhere)."""

from __future__ import annotations

import json

from fno.ingestion.news import codes
from fno.ingestion.news.pages import model
from fno.ingestion.news.reads import run as run_module
from fno.ingestion.news.reads.read_file import parse_read
from fno.ingestion.news.write_once import WriteOnceWriter  # noqa: F401  (the writer is the only way to write)
from tests.ingestion.news.reads.helpers import Page, World, wrapper_item

OUTLET = "https://outlet.example/story/{n}"


def test_a_resolved_google_news_article_is_read_at_its_resolved_url_and_one_read_file_is_written(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    world.resolve_all()
    report = world.read()
    assert report.ok and report.counts["asked"] == 1 and report.pages["written"] == 1
    assert len(world.fetcher.asked) == 1 and world.fetcher.asked[0].startswith("https://outlet.example/story/")
    (path,) = world.read_files()
    read = parse_read((world.drive.folder / path).read_bytes())
    assert read.host == "outlet.example" and read.access == "full" and read.provider == "Zz Outlet"


def test_a_google_news_article_that_is_not_resolved_yet_is_not_read_and_nothing_is_requested(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    report = world.read()
    assert report.counts["unresolved"] == 1 and world.fetcher.asked == [] and world.read_files() == []


def test_a_publisher_article_is_read_at_its_own_canonical_link(tmp_path):
    world = World(tmp_path)
    world.add_publisher(7)
    report = world.read()
    assert report.pages["written"] == 1 and world.fetcher.asked == ["https://pub.example/p/7"]


def test_an_article_on_an_outlet_we_may_not_read_makes_no_request(tmp_path):
    from fno.ingestion.news.resolve.model import RESOLVED, Resolved

    world = World(tmp_path)
    world.add(wrapper_item(1))
    world.resolver.answers["https://wrap.svc.example/rss/articles/CBMi0001?oc=5"] = Resolved(
        RESOLVED, "https://unlisted.example/a"
    )  # resolved to a host that is not on the allowlist
    world.resolve_all()
    report = world.read()
    assert report.counts["unlisted"] == 1 and world.fetcher.asked == [] and world.read_files() == []


def test_the_probe_fetches_and_extracts_but_writes_nothing(tmp_path):
    world = World(tmp_path)
    world.add_publisher(1)
    report = world.read(apply=False)
    assert report.pages["would_write"] == 1 and world.read_files() == [] and len(world.fetcher.asked) == 1
    assert "probe" in report.line() and not (world.record.manifest_folder / "reads.csv").exists()


def test_an_article_already_read_is_not_fetched_again(tmp_path):
    world = World(tmp_path)
    world.add_publisher(1)
    world.read()
    again = world.read()
    assert again.counts["already"] == 1 and again.counts["asked"] == 0 and len(world.fetcher.asked) == 1


def test_a_page_with_no_facts_writes_nothing_and_is_tried_again_next_pass(tmp_path):
    world = World(tmp_path)
    world.add_publisher(1)
    world.fetcher.answers["https://pub.example/p/1"] = Page(
        model.OK, "https://pub.example/p/1", body=b"<html>front</html>"
    )
    first = world.read()
    assert first.pages["no_facts"] == 1 and world.read_files() == []
    del world.fetcher.answers["https://pub.example/p/1"]
    assert world.read().pages["written"] == 1


def test_at_most_eighty_pages_are_fetched_whatever_limit_is_asked(tmp_path):
    world = World(tmp_path)
    world.add_publisher(*range(1, 91))
    report = world.read(pages=500)
    assert report.counts["asked"] == 80 and len(world.fetcher.asked) == 80


def test_the_newest_day_is_read_first(tmp_path):
    world = World(tmp_path)
    world.add_publisher(1, days_ago=2)
    world.add_publisher(2, days_ago=0)
    world.add_publisher(3, days_ago=1)
    world.read(pages=2)
    assert world.fetcher.asked == ["https://pub.example/p/2", "https://pub.example/p/3"]


def test_articles_older_than_the_look_back_are_not_read(tmp_path):
    world = World(tmp_path)
    world.add_publisher(1, days_ago=4)
    assert world.read().counts["examined"] == 0 and world.fetcher.asked == []


def test_the_run_stops_at_its_time_budget_and_counts_and_alerts_the_pages_it_did_not_reach(tmp_path):
    """judge 88: no per-page wall clock exists, so the run owns the budget."""
    world = World(tmp_path)
    world.add_publisher(1, 2, 3, 4, 5)
    world.fetcher.on_fetch = lambda: setattr(world.clock, "now", world.clock.now + 400.0)
    report = world.read(budget=900.0)
    assert len(world.fetcher.asked) == 3 and report.counts["budget_stopped"] == 2 and report.needs_attention


def test_a_reader_that_gets_nothing_is_red_and_alerted_but_robots_and_stops_are_not_faults(tmp_path):
    world = World(tmp_path)
    world.add_publisher(1, 2, 3)
    for n in (1, 2, 3):
        world.fetcher.answers[f"https://pub.example/p/{n}"] = Page(model.REFUSED, "")
    report = world.read()
    assert not report.ok and report.rejected[codes.READER_FAILING] == 1
    quiet = World(tmp_path / "q")
    quiet.add_publisher(1, 2, 3)
    for n in (1, 2, 3):
        quiet.fetcher.answers[f"https://pub.example/p/{n}"] = Page(model.ROBOTS_DISALLOWED, "")
    assert quiet.read().ok  # an outlet that asks not to be read is not a failing reader


def test_under_half_of_a_batch_of_ten_read_is_red_and_half_is_not(tmp_path):
    for fine, red in ((4, True), (5, False)):
        world = World(tmp_path / str(fine))
        world.add_publisher(*range(1, 11))
        for n in range(fine + 1, 11):
            world.fetcher.answers[f"https://pub.example/p/{n}"] = Page(model.HTTP_ERROR, "")
        assert (not world.read().ok) is red


def test_one_or_two_failed_pages_are_not_a_failing_reader(tmp_path):
    world = World(tmp_path)
    world.add_publisher(1, 2)
    for n in (1, 2):
        world.fetcher.answers[f"https://pub.example/p/{n}"] = Page(model.ERROR, "")
    assert world.read().ok


def test_the_read_cap_counts_what_it_left_unread_and_alerts(tmp_path, monkeypatch):
    monkeypatch.setattr(run_module, "MAX_RECORD_READS", 2)
    world = World(tmp_path)
    world.add_publisher(1, 2, 3, 4, 5)
    report = world.read()
    assert report.counts["examined"] == 2 and report.counts["unexamined"] == 3 and report.needs_attention


def test_a_read_file_with_other_bytes_is_a_conflict_and_is_never_overwritten(tmp_path):
    world = World(tmp_path)
    world.add_publisher(1)
    world.read()
    (path,) = world.read_files()
    (world.drive.folder / path).write_bytes(b"{}")
    (world.record.manifest_folder / "reads.csv").unlink()
    report = world.read()
    assert (
        not report.ok
        and report.rejected[codes.READ_CONFLICT] == 1
        and (world.drive.folder / path).read_bytes() == b"{}"
    )


def test_a_torn_reads_manifest_stops_the_pass_before_any_request(tmp_path):
    world = World(tmp_path)
    world.add_publisher(1)
    row = "2026-10-27," + "a" * 64 + ",recorded," + "b" * 64 + ",10"
    (world.record.manifest_folder / "reads.csv").write_text("date,article_id,status,sha256,size_bytes\n" + row)
    report = world.read()
    assert not report.ok and report.rejected[codes.MANIFEST_BROKEN] == 1 and world.fetcher.asked == []


def test_the_read_file_holds_no_body_and_the_line_holds_no_link_key_or_host(tmp_path):
    world = World(tmp_path)
    world.add_publisher(1)
    report = world.read()
    (path,) = world.read_files()
    assert b"word word" not in (world.drive.folder / path).read_bytes()
    line = report.line()
    assert line.startswith("news read-pages (applied): ") and "pub.example" not in line and "Zzpub" not in line
    assert json.loads((world.drive.folder / path).read_bytes())["host"] == "pub.example"
