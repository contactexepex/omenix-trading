"""NP11: which feed found which article, kept in sealed private files only, written for closed days, never rewritten."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FEEDS_FOLDER, FeedListError, parse_feed_list
from fno.ingestion.news.provenance import file, writer
from fno.ingestion.news.provenance.model import BROAD, TARGETED, UNKNOWN, path_of, seal_of
from fno.ingestion.news.record import wiring
from tests.ingestion.news.article.samples import rss, rss_item
from tests.ingestion.news.fakes import SALT
from tests.ingestion.news.record.helpers import POLL_AT
from tests.ingestion.news.record.test_wiring import RecordingDrive, stage, world  # noqa: F401

DAY = POLL_AT.date()
LATER = DAY + timedelta(days=3)  # "today" for a run that should write DAY
ITEM = rss(rss_item(title="Zzalpha posts a record quarter", link="https://pub.example/a/1", guid="g1"))
OTHER = rss(rss_item(title="Zzbeta wins a contract", link="https://pub.example/a/2", guid="g2"))


def feed_list(drive, version, *feeds):
    entries = [
        {"id": i, "url": f"https://h{n}.example/rss", **({"scope": s} if s else {})} for n, (i, s) in enumerate(feeds)
    ]
    drive.put(f"config/{FEEDS_FOLDER}/feeds-v{version}.json", json.dumps({"salt": SALT, "feeds": entries}).encode())


def promote(monkeypatch, today=LATER):
    monkeypatch.setattr(writer, "now_utc", lambda: today_moment(today))
    return wiring.build_news_promotion().promote(DAY, DAY + timedelta(days=1))


def today_moment(day):
    return POLL_AT.replace(year=day.year, month=day.month, day=day.day)


def day_files(drive):
    folder = drive.folder / "raw/news/provenance/1"
    return sorted(p.name for p in folder.glob("*.json")) if folder.exists() else []


def pairs_of(drive, name):
    return file.parse((drive.folder / "raw/news/provenance/1" / name).read_bytes())


def test_a_closed_days_file_lists_every_feed_that_found_an_article_with_its_scope(world, monkeypatch):  # noqa: F811
    feed_list(world, 1, ("feed-01", BROAD), ("q-0123456789ab", TARGETED), ("feed-02", None))
    for feed in ("feed-01", "q-0123456789ab", "feed-02"):
        stage(world, feed, ITEM)
    report = promote(monkeypatch)
    assert report.ok and day_files(world) == [f"{DAY}.json"]
    (pairs,) = pairs_of(world, f"{DAY}.json").values()
    assert pairs == {("feed-01", BROAD), ("q-0123456789ab", TARGETED), ("feed-02", UNKNOWN)}


def test_the_bytes_are_sorted_sealed_and_the_same_on_every_run(world, monkeypatch):  # noqa: F811
    feed_list(world, 1, ("feed-02", None), ("feed-01", BROAD))
    stage(world, "feed-02", ITEM)
    stage(world, "feed-01", ITEM)
    promote(monkeypatch)
    first = (world.folder / "raw/news/provenance/1" / f"{DAY}.json").read_bytes()
    document = json.loads(first)
    assert (
        document["seal"] == seal_of(SALT, path_of(DAY))
        and first == json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    )
    (feeds,) = document["pairs"].values()
    assert feeds == sorted(feeds)
    again = promote(monkeypatch)
    assert (
        again.ok
        and day_files(world) == [f"{DAY}.json"]
        and (world.folder / "raw/news/provenance/1" / f"{DAY}.json").read_bytes() == first
    )


def test_without_the_seal_the_file_could_be_rebuilt_from_public_values_and_with_it_it_cannot(world, monkeypatch):  # noqa: F811
    feed_list(world, 1, ("feed-01", BROAD))
    stage(world, "feed-01", ITEM)
    promote(monkeypatch)
    stored = (world.folder / "raw/news/provenance/1" / f"{DAY}.json").read_bytes()
    (key,) = json.loads(stored)["pairs"]
    guess = {("feed-01", BROAD)}
    rebuilt = file.to_bytes(DAY, 0, "a-guessed-salt-" + "x" * 8, {key: frozenset(guess)})
    assert rebuilt != stored  # a guesser who knows the key, the feed id and the scope still cannot match the SHA-256
    assert file.to_bytes(DAY, 0, SALT, {key: frozenset(guess)}) == stored
    assert file.to_bytes(DAY, 1, SALT, {key: frozenset(guess)}) != stored  # the seal follows the path


def test_the_open_day_is_not_written(world, monkeypatch):  # noqa: F811
    feed_list(world, 1, ("feed-01", BROAD))
    stage(world, "feed-01", ITEM)
    report = promote(monkeypatch, today=DAY)
    assert report.ok and day_files(world) == []


def test_a_late_poll_goes_to_a_numbered_supplement_and_the_day_file_is_never_rewritten(world, monkeypatch):  # noqa: F811
    feed_list(world, 1, ("feed-01", BROAD), ("q-0123456789ab", TARGETED))
    stage(world, "feed-01", ITEM)
    promote(monkeypatch)
    day_file = (world.folder / "raw/news/provenance/1" / f"{DAY}.json").read_bytes()
    stage(world, "q-0123456789ab", ITEM, POLL_AT + timedelta(hours=1))
    stage(world, "feed-01", OTHER, POLL_AT + timedelta(hours=2))
    promote(monkeypatch)
    assert day_files(world) == [f"{DAY}-1.json", f"{DAY}.json"]
    assert (world.folder / "raw/news/provenance/1" / f"{DAY}.json").read_bytes() == day_file
    supplement = pairs_of(world, f"{DAY}-1.json")
    assert sorted(len(v) for v in supplement.values()) == [1, 1] and {p for v in supplement.values() for p in v} == {
        ("q-0123456789ab", TARGETED),
        ("feed-01", BROAD),
    }
    promote(monkeypatch)  # nothing new: no third file
    assert day_files(world) == [f"{DAY}-1.json", f"{DAY}.json"]


def test_the_manifest_and_the_receipts_name_no_feed_no_key_and_no_pair(world, monkeypatch, tmp_path):  # noqa: F811
    feed_list(world, 1, ("feed-01", BROAD), ("q-0123456789ab", TARGETED))
    stage(world, "feed-01", ITEM)
    stage(world, "q-0123456789ab", ITEM)
    promote(monkeypatch)
    (key,) = pairs_of(world, f"{DAY}.json")
    row = (tmp_path / "repo" / "manifests" / "provenance.csv").read_text()
    assert f"{DAY}" in row and "recorded" in row
    for secret in ("feed-01", "q-0123456789ab", key, "broad", "targeted"):
        assert secret not in row
    lines = [
        line
        for receipt in (tmp_path / "repo" / "receipts").rglob("*")
        if receipt.is_file()
        for line in receipt.read_text().splitlines()
        if "news/provenance/" in line
    ]
    assert len(lines) == 1 and f"news/provenance/1/{DAY}.json" in lines[0]
    for secret in ("feed-01", "q-0123456789ab", key, "broad", "targeted"):
        assert secret not in lines[0]


def test_a_poll_that_cannot_be_read_is_counted_and_a_damaged_day_is_left_alone(world, monkeypatch):  # noqa: F811
    feed_list(world, 1, ("feed-01", BROAD))
    stage(world, "feed-01", b"not a feed at all")
    stage(world, "feed-01", ITEM, POLL_AT + timedelta(hours=1))
    report = promote(monkeypatch)
    assert report.rejected[codes.PROVENANCE_POLL_SKIPPED] == 1
    world.put(f"raw/news/provenance/1/{DAY}-1.json", b"damaged")
    stage(world, "feed-01", OTHER, POLL_AT + timedelta(hours=2))
    report = promote(monkeypatch)
    assert report.rejected[codes.PROVENANCE_UNREADABLE] == 1
    assert (world.folder / "raw/news/provenance/1" / f"{DAY}-1.json").read_bytes() == b"damaged"


def test_a_scope_is_broad_targeted_or_absent_and_an_old_list_without_one_still_parses():
    base = {"salt": "s" * 16, "feeds": [{"id": "feed-01", "url": "https://h.example/rss"}]}
    assert parse_feed_list(json.dumps(base).encode(), 1).feeds[0].scope == ""
    for scope in (BROAD, TARGETED):
        base["feeds"][0]["scope"] = scope
        assert parse_feed_list(json.dumps(base).encode(), 1).feeds[0].scope == scope
    for bad in ("Broad", "unknown", "", 1, None):
        base["feeds"][0]["scope"] = bad
        if bad == "":
            continue
        with pytest.raises(FeedListError):
            parse_feed_list(json.dumps(base).encode(), 1)


def test_a_feed_with_no_label_is_unknown_never_guessed_from_its_id_and_a_newer_list_relabels(world):  # noqa: F811
    from fno.ingestion.news.feeds import PrivateFeedLists
    from fno.ingestion.storage.raw_store import AreaStore

    feed_list(world, 1, ("q-0123456789ab", None), ("feed-01", BROAD))
    feed_list(world, 2, ("q-0123456789ab", TARGETED))
    scopes = PrivateFeedLists(AreaStore(world, "config")).scopes_ever_listed()
    assert scopes == {"q-0123456789ab": TARGETED, "feed-01": BROAD}
    feed_list(world, 3, ("q-0123456789ab", None))
    assert PrivateFeedLists(AreaStore(world, "config")).scopes_ever_listed()["q-0123456789ab"] == UNKNOWN


def test_the_feed_plan_labels_publisher_feeds_and_broad_queries_broad_and_company_queries_targeted():
    from fno.ingestion.news.planning.planner import plan_feeds
    from tests.ingestion.news.planning.helpers import SALT as PLAN_SALT
    from tests.ingestion.news.planning.helpers import companies, company, discovery

    plan = plan_feeds(companies(company("ZZA", "Zzalpha", True)), discovery(), PLAN_SALT)
    feeds = json.loads(plan.data)["feeds"]
    assert sorted(f["scope"] for f in feeds) == sorted(
        [BROAD] * (plan.publisher + plan.broad) + [TARGETED] * plan.targeted
    )
    assert plan.targeted == 1 and all(f["scope"] == BROAD for f in feeds if f["kind"] == "publisher")


def test_an_article_holds_no_feed_so_a_later_poll_by_another_feed_is_never_a_revision():
    from dataclasses import fields

    from fno.ingestion.news.article.article_file import Article

    assert [f.name for f in fields(Article)] == [
        "key", "kind", "source", "title", "summary", "canonical_url", "published_at", "time_source",
        "first_seen_at", "source_domain", "wrapper_link",
    ]  # fmt: skip


def test_pairs_are_written_sorted_whatever_order_they_come_in():
    pairs = {"k": (("feed-02", BROAD), ("feed-01", BROAD), ("q-0123456789ab", TARGETED))}
    listed = json.loads(file.to_bytes(DAY, 0, SALT, pairs))["pairs"]["k"]
    assert listed == sorted(listed) and listed[0] == ["feed-01", BROAD]


def daily(monkeypatch, run_day):
    """What the scheduled job does: a run for one day only, on that day."""
    monkeypatch.setattr(writer, "now_utc", lambda: today_moment(run_day))
    return wiring.build_news_promotion().promote(run_day, run_day)


def test_daily_runs_for_today_only_still_write_yesterdays_provenance_the_next_day(world, monkeypatch):  # noqa: F811
    """Judge 123 B1: pairs came only from the polls of the run's own range, so a routine daily run wrote none."""
    feed_list(world, 1, ("feed-01", BROAD), ("q-0123456789ab", TARGETED))
    stage(world, "feed-01", ITEM)
    stage(world, "q-0123456789ab", ITEM, POLL_AT + timedelta(hours=1))
    assert daily(monkeypatch, DAY).ok and day_files(world) == []  # the day is still open
    report = daily(monkeypatch, DAY + timedelta(days=1))
    assert report.ok and day_files(world) == [f"{DAY}.json"]
    (pairs,) = pairs_of(world, f"{DAY}.json").values()
    assert pairs == {("feed-01", BROAD), ("q-0123456789ab", TARGETED)}
    daily(monkeypatch, DAY + timedelta(days=2))
    assert day_files(world) == [f"{DAY}.json"]  # a day with a file is not written again


def test_an_ist_day_is_read_from_the_two_utc_days_that_cover_it(world, monkeypatch):  # noqa: F811
    """IST day D starts at UTC D-1 18:30: a poll at 20:00 UTC on D-1 belongs to D."""
    feed_list(world, 1, ("feed-01", BROAD))
    evening = (POLL_AT - timedelta(days=1)).replace(hour=20)
    stage(world, "feed-01", ITEM, evening)  # 01:30 IST on DAY
    stage(world, "feed-01", OTHER, POLL_AT)
    daily(monkeypatch, DAY + timedelta(days=1))
    assert day_files(world) == [f"{DAY}.json"]
    assert len(pairs_of(world, f"{DAY}.json")) == 2


def test_polls_whose_pairs_could_not_be_recorded_are_counted_not_silent(world, monkeypatch):  # noqa: F811
    feed_list(world, 1, ("feed-01", BROAD))
    stage(world, "feed-01", ITEM)
    stage(world, "feed-01", OTHER, POLL_AT + timedelta(hours=1))
    real_put = world.put

    def failing(path, data):
        if "provenance" in path:
            raise OSError("Drive down")
        real_put(path, data)

    monkeypatch.setattr(world, "put", failing)
    report = daily(monkeypatch, DAY + timedelta(days=1))
    assert report.rejected[codes.PROVENANCE_FAILED] == 1 and report.rejected[codes.PROVENANCE_POLLS_MISSING] == 2
    assert day_files(world) == []


def test_a_poll_at_2000_utc_belongs_to_the_next_ist_day_and_that_day_closes_by_ist_not_utc(world, monkeypatch):  # noqa: F811
    """Judge 124 B2: the day of a poll is its IST date; 20:00 UTC on D is 01:30 IST on D+1."""
    feed_list(world, 1, ("feed-01", BROAD))
    stage(world, "feed-01", ITEM, POLL_AT.replace(hour=20))
    # at 18:45 UTC on DAY+1 it is already DAY+2 in IST, so IST day DAY+1 is closed only after 18:30 UTC on DAY+1
    monkeypatch.setattr(writer, "now_utc", lambda: POLL_AT.replace(hour=12))
    assert wiring.build_news_promotion().promote(DAY, DAY).ok and day_files(world) == []
    monkeypatch.setattr(writer, "now_utc", lambda: POLL_AT.replace(day=DAY.day + 1, hour=20))
    assert wiring.build_news_promotion().promote(DAY, DAY + timedelta(days=1)).ok
    assert day_files(world) == [f"{DAY + timedelta(days=1)}.json"]


def test_one_damaged_day_file_does_not_stop_the_sweep_of_the_other_days(world, monkeypatch):  # noqa: F811
    """Judge 123 C1: a damaged file of an old day used to switch the sweep off for every day, silently."""
    feed_list(world, 1, ("feed-01", BROAD))
    stage(world, "feed-01", ITEM)
    world.put(f"raw/{path_of(DAY - timedelta(days=3))}", b"damaged")
    report = daily(monkeypatch, DAY + timedelta(days=1))
    assert day_files(world) == [f"{DAY - timedelta(days=3)}.json", f"{DAY}.json"]
    assert report.rejected[codes.PROVENANCE_UNREADABLE] == 1 and not report.ok
