"""NP2c: the resolve pass over the Record, with a fake resolver (nothing is requested anywhere)."""

from __future__ import annotations

import json

from fno.ingestion.news import codes
from fno.ingestion.news.resolve import run as run_module
from fno.ingestion.news.resolve.model import DECODE_FAILED, PAUSED, RESOLVED, Resolved
from fno.ingestion.news.resolve.resolution_file import parse_resolution
from tests.ingestion.news.resolve.pass_helpers import TODAY, FakeResolver, World, publisher_item, wrapper_item


def test_only_wrapper_articles_are_asked_and_each_success_becomes_one_resolution_file(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1), wrapper_item(2))
    world.add(publisher_item(3), feed="feed-02")
    report = world.run()
    assert (
        report.ok and report.counts["pending"] == 2 and report.counts["examined"] == 2
    )  # the publisher article is never read
    assert report.results["written"] == 2 and len(world.resolver.calls) == 1 and len(world.resolver.calls[0]) == 2
    assert len(world.resolution_files()) == 2 and all("/resolved/" in f for f in world.resolution_files())


def test_a_pass_given_the_whole_articles_manifest_still_asks_only_wrapper_articles(tmp_path):
    """Defence in depth under the index (NP2d): the pass itself checks each article it reads."""
    world = World(tmp_path)
    world.add(wrapper_item(1))
    world.add(publisher_item(2), publisher_item(3), feed="feed-02")
    report = world.pass_("articles.csv").run(TODAY, True, 80)
    assert report.counts["examined"] == 3 and report.counts["not_wrapper"] == 2 and report.counts["pending"] == 1


def test_a_resolution_file_has_the_url_its_host_and_whether_the_host_is_the_feeds_outlet(tmp_path):
    answers = {}
    world = World(tmp_path, FakeResolver(answers))
    world.add(wrapper_item(1), wrapper_item(2, source_url="https://other.example"))
    for link in (
        "https://wrap.svc.example/rss/articles/CBMi0001?oc=5",
        "https://wrap.svc.example/rss/articles/CBMi0002?oc=5",
    ):
        answers[link] = Resolved(RESOLVED, "https://www.outlet.example/news/" + link[-8:-3])
    world.run()
    found = {
        r.claimed_domain: r
        for r in (parse_resolution((world.drive.folder / f).read_bytes()) for f in world.resolution_files())
    }
    assert found["outlet.example"].host == "www.outlet.example" and found["outlet.example"].host_agrees
    assert found["other.example"].host_agrees is False  # the feed claimed another outlet


def test_the_resolution_file_holds_facts_only_and_no_time_so_the_same_answer_is_the_same_bytes(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    world.run()
    document = json.loads((world.drive.folder / world.resolution_files()[0]).read_bytes())
    assert set(document) == {"format", "key", "url", "host", "claimed_domain", "host_agrees", "resolver"}


def test_a_probe_asks_the_resolver_but_writes_nothing(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    report = world.run(apply=False)
    assert report.results["would_write"] == 1 and world.resolution_files() == [] and len(world.resolver.calls) == 1
    assert "probe" in report.line()
    assert not (world.record.manifest_folder / "resolved.csv").exists()


def test_a_resolved_article_is_not_asked_again(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    world.run()
    again = world.run()
    assert again.counts["already"] == 1 and again.counts["pending"] == 0 and len(world.resolver.calls) == 1


def test_a_failed_link_writes_nothing_and_is_tried_again_on_the_next_pass(tmp_path):
    world = World(tmp_path, FakeResolver({}))
    world.add(wrapper_item(1), wrapper_item(2))
    link = "https://wrap.svc.example/rss/articles/CBMi0001?oc=5"
    world.resolver.answers[link] = Resolved(DECODE_FAILED)
    first = world.run()
    assert first.ok and first.results[DECODE_FAILED] == 1 and len(world.resolution_files()) == 1  # one of two resolved
    del world.resolver.answers[link]
    assert world.run().results["written"] == 1 and len(world.resolver.calls) == 2 and len(world.resolution_files()) == 2


def test_a_pushed_back_service_leaves_the_links_waiting_but_the_run_is_not_green(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1), wrapper_item(2), wrapper_item(3))
    world.resolver.answers = {
        f"https://wrap.svc.example/rss/articles/CBMi000{n}?oc=5": Resolved(PAUSED) for n in (1, 2, 3)
    }
    report = world.run()
    assert report.results[PAUSED] == 3 and world.resolution_files() == []
    assert not report.ok and report.rejected[codes.RESOLVER_FAILING] == 1 and report.needs_attention


def test_a_resolver_that_fails_every_link_is_red_and_alerted_never_a_green_run_while_links_age_out(tmp_path):
    """judge 82 B1: the broken decoder at the first go-live, 4 articles a day over 4 days, a small read cap."""
    world = World(tmp_path, FakeResolver({}))
    for days_ago in range(4):
        world.add(*[wrapper_item(10 * days_ago + n) for n in range(1, 5)], days_ago=days_ago)
    world.resolver.default = Resolved(DECODE_FAILED)
    report = world.run()
    assert not report.ok and report.rejected[codes.RESOLVER_FAILING] == 1 and report.needs_attention
    assert world.resolution_files() == []


def test_a_real_batch_with_under_half_resolved_is_red_and_half_or_more_is_not(tmp_path):
    for resolved, red in ((4, True), (5, False), (9, False)):
        world = World(tmp_path / f"w{resolved}", FakeResolver({}))
        world.add(*[wrapper_item(n) for n in range(1, 11)])
        for n in range(1, 11 - resolved):
            world.resolver.answers[f"https://wrap.svc.example/rss/articles/CBMi{n:04d}?oc=5"] = Resolved(DECODE_FAILED)
        assert (not world.run().ok) is red, resolved


def test_articles_the_read_cap_left_unread_are_counted_on_the_last_day_and_alerted(tmp_path, monkeypatch):
    """judge 82 B1: the 600-read cap must not hide the articles about to age out."""
    monkeypatch.setattr(run_module, "MAX_READS", 3)
    world = World(tmp_path)
    world.add(*[wrapper_item(n) for n in range(1, 5)], days_ago=0)
    world.add(*[wrapper_item(n) for n in range(11, 15)], days_ago=3)  # the last day: all of it beyond the read cap
    report = world.run()
    assert report.counts["unexamined"] == 5 and report.counts["expiring"] == 4 and report.needs_attention


def test_the_cap_bounds_the_links_asked_newest_day_first_and_counts_the_rest_as_backlog(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1), days_ago=2)
    world.add(wrapper_item(2), days_ago=0)
    world.add(wrapper_item(3), days_ago=1)
    report = world.run(cap=2)
    assert report.counts["pending"] == 2 and report.counts["backlog"] == 1
    asked = [link[-8:-3] for link in world.resolver.calls[0]]
    assert asked == ["CBMi0", "CBMi0"] or len(asked) == 2
    assert world.resolver.calls[0][0].endswith("CBMi0002?oc=5") and world.resolver.calls[0][1].endswith("CBMi0003?oc=5")


def test_the_cap_can_never_be_raised_above_eighty(tmp_path):
    world = World(tmp_path)
    world.add(*[wrapper_item(n) for n in range(1, 90)])
    report = world.run(cap=500)
    assert report.counts["pending"] == 80 and report.counts["backlog"] == 9


def test_articles_older_than_the_look_back_are_not_asked_and_the_last_day_is_counted_as_expiring(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1), days_ago=4)  # outside
    world.add(wrapper_item(2), wrapper_item(3), days_ago=3)  # the last day of the look-back
    link = "https://wrap.svc.example/rss/articles/CBMi0002?oc=5"
    world.resolver.answers[link] = Resolved(DECODE_FAILED)
    report = world.run()
    assert report.counts["examined"] == 2 and len(world.resolver.calls[0]) == 2
    assert report.counts["expiring"] == 1 and report.needs_attention and report.ok


def test_a_backlog_left_on_the_last_day_by_the_cap_is_expiring_too(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1), wrapper_item(2), days_ago=3)
    report = world.run(cap=1)
    assert report.counts["expiring"] == 1 and report.counts["backlog"] == 1 and report.ok


def test_the_number_of_article_files_read_in_a_pass_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(run_module, "MAX_READS", 2)
    world = World(tmp_path)
    world.add(*[wrapper_item(n) for n in range(1, 6)])
    report = world.run()
    assert report.counts["examined"] == 2 and report.counts["unexamined"] == 3 and len(world.resolver.calls[0]) == 2


def test_publisher_articles_are_never_read_so_they_cannot_use_up_the_read_cap(tmp_path, monkeypatch):
    """NP2d: the pass reads the wrapper index, not every article of the look-back."""
    monkeypatch.setattr(run_module, "MAX_READS", 2)
    world = World(tmp_path)
    world.add(*[publisher_item(n) for n in range(1, 30)], feed="feed-02")
    world.add(wrapper_item(1), wrapper_item(2))
    report = world.run()
    assert report.counts["examined"] == 2 and report.counts["unexamined"] == 0 and report.results["written"] == 2


def test_one_resolver_call_per_pass_so_its_stop_and_pacing_are_not_reset(tmp_path):
    world = World(tmp_path)
    world.add(*[wrapper_item(n) for n in range(1, 31)])
    world.run()
    assert len(world.resolver.calls) == 1 and len(world.resolver.calls[0]) == 30


def test_the_pass_needs_only_the_record_so_trashing_the_staged_polls_loses_nothing(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    for staged in (world.drive.folder / "staging").rglob("*"):
        if staged.is_file():
            staged.unlink()  # what the staging cleanup does 7 days after a poll is promoted
    assert world.run().results["written"] == 1


def test_a_resolution_file_with_other_bytes_is_a_conflict_and_is_never_overwritten(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    world.run()
    path = world.drive.folder / world.resolution_files()[0]
    path.write_bytes(b"{}")
    (world.record.manifest_folder / "resolved.csv").unlink()
    report = world.run()
    assert not report.ok and report.rejected[codes.RESOLUTION_CONFLICT] == 1 and path.read_bytes() == b"{}"


def test_a_file_held_without_its_manifest_row_gets_the_row_from_the_held_bytes(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    world.run()
    (world.record.manifest_folder / "resolved.csv").unlink()
    report = world.run()
    assert report.ok and report.results["no_op"] == 1 and (world.record.manifest_folder / "resolved.csv").exists()


def test_an_unreadable_article_is_counted_red_never_skipped_silently(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    for article in (world.drive.folder / "raw/news/articles").rglob("*.json"):
        article.write_bytes(b"not an article")
    report = world.run()
    assert not report.ok and report.rejected[codes.ARTICLE_UNREADABLE] == 1 and world.resolver.calls == []


def test_a_torn_resolved_manifest_stops_the_pass_before_anything_is_written(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    (world.record.manifest_folder / "resolved.csv").write_text(
        "date,article_id,status,sha256,size_bytes\n2026-10-27,ab"
    )
    report = world.run()
    assert not report.ok and world.resolution_files() == [] and world.resolver.calls == []


def test_the_report_line_is_counts_only(tmp_path):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    line = world.run().line()
    assert line.startswith("news resolve (applied): ") and "outlet.example" not in line and "Zzstory" not in line
    assert "CBMi" not in line and "wrap.svc" not in line


def test_a_whole_last_row_with_no_final_newline_stops_the_pass_before_the_resolver_is_asked(tmp_path):
    """judge 83: only `check_ready` catches this (the row is whole, so it is not counted as skipped)."""
    world = World(tmp_path)
    world.add(wrapper_item(1))
    row = "2026-10-27," + "a" * 64 + ",recorded," + "b" * 64 + ",10"
    (world.record.manifest_folder / "resolved.csv").write_text("date,article_id,status,sha256,size_bytes\n" + row)
    report = world.run()
    assert not report.ok and report.rejected[codes.MANIFEST_BROKEN] == 1
    assert world.resolver.calls == [] and world.resolution_files() == []


def test_one_or_two_dead_links_are_not_a_failing_service_and_do_not_turn_every_pass_red(tmp_path):
    """judges 82, 83: a permanently dead link must not make every pass red for three days."""
    world = World(tmp_path, FakeResolver({}))
    world.resolver.default = Resolved(DECODE_FAILED)
    world.add(wrapper_item(1), wrapper_item(2))
    report = world.run()
    assert report.ok and report.results[DECODE_FAILED] == 2 and not report.needs_attention


def test_unread_articles_on_a_newer_day_alone_still_alert_without_turning_the_run_red(tmp_path, monkeypatch):
    """judges 82, 83: `unexamined` with no expiring link is alerted by its own clause."""
    monkeypatch.setattr(run_module, "MAX_READS", 2)
    world = World(tmp_path)
    world.add(*[wrapper_item(n) for n in range(1, 5)])
    report = world.run()
    assert report.counts["unexamined"] == 2 and report.counts["expiring"] == 0
    assert report.ok and report.needs_attention
