"""NP3b: the command, the widened feed id and the per-run pacer built from the feed list."""

from __future__ import annotations

import json
from argparse import Namespace

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news import job as job_module
from fno.ingestion.news.article.keys import PUBLISHER, WRAPPER
from fno.ingestion.news.feeds import FEED_ID, FeedEntry, FeedList, PrivateFeedLists, parse_feed_list
from fno.ingestion.news.pacing import WRAPPER_SPACING_SECONDS, pacer_for
from fno.ingestion.news.planning import cli as plan_cli
from fno.ingestion.news.planning import wiring
from fno.ingestion.news.session import NewsSession
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore
from fno.shared.nse_pacer import DEFAULT_SPACING_SECONDS, HOST_SPACING_SECONDS
from tests.ingestion.news.planning.helpers import discovery_document

COMPANIES = [{"symbol": "ZZA", "name": "Zzalpha Marker", "targeted": True}, {"symbol": "ZZB", "name": "Zzbeta"}]
COMPANY_FILE = json.dumps({"format": 1, "companies": COMPANIES}).encode()


class World:
    def __init__(self, tmp_path, monkeypatch):
        self.drive = LocalFolderStore(tmp_path / "drive")
        self.config = AreaStore(self.drive, "config")
        monkeypatch.setattr(wiring, "build_owner_drive", lambda env=None: self.drive)
        self.config.put("companies/companies-v1.json", COMPANY_FILE)
        self.config.put("discovery/discovery-v1.json", json.dumps(discovery_document()).encode())
        self.lines: list[str] = []

    def run(self, apply: bool) -> int:
        return plan_cli.cmd_plan_feeds(Namespace(apply=apply), out=self.lines.append)

    def feed_files(self) -> list[str]:
        return sorted(self.config.checksums("feeds"))


def test_without_apply_nothing_is_written_and_the_line_is_counts_only(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    assert world.run(False) == 0 and world.feed_files() == []
    assert world.lines == [
        "news plan-feeds (report only): feeds 4 (broad 2, targeted 1, publisher 1), new 4, dropped 0"
    ]
    assert not any(word in world.lines[0] for word in ("Zzalpha", "Marker", "zzmarket", "search.svc", "feed-01"))


def test_the_first_plan_gets_a_fresh_salt_and_the_next_keeps_it_and_every_planned_id(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    assert world.run(True) == 0 and world.feed_files() == ["feeds-v1.json"]
    first = parse_feed_list(world.config.get("feeds/feeds-v1.json"), 1)
    assert len(first.salt) >= 32 and first.salt.isalnum()
    world.config.put("companies/companies-v2.json", json.dumps({"format": 1, "companies": [
        {"symbol": "ZZA", "name": "Zzalpha Marker", "targeted": True},
        {"symbol": "ZZB", "name": "Zzbeta", "targeted": True}]}).encode())  # fmt: skip
    assert world.run(True) == 0 and world.feed_files() == ["feeds-v1.json", "feeds-v2.json"]
    second = parse_feed_list(world.config.get("feeds/feeds-v2.json"), 2)
    assert second.salt == first.salt and {f.feed_id for f in first.feeds} < {f.feed_id for f in second.feeds}
    assert world.lines[-1].endswith("new 1, dropped 0")


def test_a_planned_list_is_read_by_the_ordinary_feed_list_reader(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.run(True)
    listed = PrivateFeedLists(world.config).latest()
    assert listed.version == 1 and {f.kind for f in listed.feeds} == {PUBLISHER, WRAPPER}


def test_a_missing_input_is_a_fixed_code_and_nothing_is_written(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    (tmp_path / "drive" / "config" / "discovery" / "discovery-v1.json").unlink()
    assert world.run(True) == 1 and world.lines == [f"news plan-feeds stopped: {codes.DISCOVERY_MISSING}"]
    assert world.feed_files() == []


def test_an_unexpected_error_prints_only_its_class(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    monkeypatch.setattr(wiring, "PrivateDiscoveryFile", lambda store: (_ for _ in ()).throw(ValueError("secret path")))
    assert world.run(False) == 1 and world.lines == [f"news plan-feeds stopped: {codes.UNEXPECTED} ValueError"]


# ---- the widened feed id ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("good", ["feed-01", "feed-123", "q-0123abcd"])
def test_the_ids_a_feed_list_accepts(good):
    assert FEED_ID.match(good)


@pytest.mark.parametrize(
    "bad", ["q-ABCDEF12", "q-123", "q-0123abcde", "feed-1", "feed-01\n", "q-0123abcd\n", "x-0123abcd", ""]
)
def test_the_ids_it_refuses_a_trailing_line_break_included(bad):
    assert not FEED_ID.match(bad)


# ---- the per-run pacer -----------------------------------------------------------------------------------------


def feed_list(*entries) -> FeedList:
    return FeedList(1, tuple(FeedEntry(*e) for e in entries))


def test_search_hosts_are_paced_1_5_seconds_apart_and_every_other_host_keeps_the_default():
    feeds = feed_list(("q-0123abcd", "https://search.svc.example/s?q=1", WRAPPER),
                      ("feed-01", "https://feeds.pub.example/rss", PUBLISHER))  # fmt: skip
    pacer = pacer_for(feeds)
    assert pacer.spacing == {"search.svc.example": WRAPPER_SPACING_SECONDS} and WRAPPER_SPACING_SECONDS == 1.5
    assert pacer.spacing.get("feeds.pub.example", DEFAULT_SPACING_SECONDS) == 1.0


def test_the_nse_spacing_table_is_not_changed_by_the_news_pacer():
    pacer_for(feed_list(("q-0123abcd", "https://search.svc.example/s?q=1", WRAPPER)))
    assert HOST_SPACING_SECONDS == {"www.nseindia.com": 1.0, "nsearchives.nseindia.com": 1.0}


def test_the_session_takes_the_pacer_of_the_run_and_the_job_sets_it_before_the_first_request():
    feeds = feed_list(("q-0123abcd", "https://search.svc.example/s?q=1", WRAPPER))
    session = NewsSession()
    before = session.pacer
    session.pace_for(feeds)
    assert session.pacer is not before and session.pacer.spacing == {"search.svc.example": 1.5}

    order = []

    class Lists:
        def latest(self, lowest, used):
            return feeds

    class Log:
        def highest_feed_list_version(self):
            return 0

        def used_feed_lists(self):
            return {}

        def note_feed_list(self, *args):
            order.append("noted")

    class Fetcher:
        def run(self, listed):
            order.append("fetched")

    class Spy:
        def pace_for(self, listed):
            order.append("paced")

    job_module.NewsFetchJob(Lists(), Fetcher(), Log(), lambda: None, Spy()).run()
    assert order == ["noted", "paced", "fetched"]
