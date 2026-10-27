"""NP6a: a version 2 cluster run: format 2 file under its own folder, the company list rules, the resolution files."""

from __future__ import annotations

import csv
import json
from datetime import timedelta

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.article.keys import WRAPPER
from fno.ingestion.news.cluster_record.article_source import ArticleSource
from fno.ingestion.news.cluster_record.cluster_file import cluster_path, parse_cluster_file
from fno.ingestion.news.cluster_record.grouping import GroupingBlocked, SymbolGrouping
from fno.ingestion.news.cluster_record.run import ClusterRun
from fno.ingestion.news.cluster_record.writer import ClusterWriter
from fno.ingestion.news.companies.model import CompanyList, CompanyListSource
from fno.ingestion.news.companies.parse import CompanyListError
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.resolve.resolution_file import Resolution, resolution_path
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import AreaStore
from tests.ingestion.news.cluster_record.helpers import AS_OF, HEADLINE, OTHER, World, item
from tests.ingestion.news.record.helpers import FEED, Setup
from tests.ingestion.news.tagging.helpers import COMPANIES

STORY = "https://pub.example/news/story-one"
SHA = "a" * 64


class Scripted(CompanyListSource):
    def __init__(self, result):
        self.result = result

    def companies(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class WorldTwo(World):
    """The same world, but the run is algorithm version 2 over a scripted company list."""

    companies: CompanyListSource = Scripted(CompanyList(7, COMPANIES, SHA))

    def build(self) -> None:
        super().build()
        record = AreaStore(self.drive, "raw")
        store = DataStore(self.drive, "raw", self.record.receipts, "news-cluster", "run-1")
        writer = ClusterWriter(record, store, self.clusters)
        grouping = SymbolGrouping(self.companies, record)
        self.run_object = ClusterRun(
            ArticleSource(record, NewsManifest(self.record.manifest_folder)), writer, record, grouping
        )

    def written(self):
        return json.loads(self.drive.get(f"raw/{cluster_path('2', AS_OF)}"))


def seeded(tmp_path, companies=None) -> WorldTwo:
    world = WorldTwo.__new__(WorldTwo)
    if companies is not None:
        world.companies = companies
    World.__init__(world, tmp_path)
    world.add(
        item(HEADLINE, STORY, 8),
        item(OTHER, "https://pub.example/b/1"),
        item("A home page link", "https://pub.example/", 9),  # identifies no story
    )
    return world


def test_a_version_two_run_writes_a_format_two_file_in_its_own_folder_with_what_fed_it(tmp_path):
    world = seeded(tmp_path)
    report = world.cluster()
    assert report.ok and world.cluster_files() == ["raw/news/clusters/2/20261027T120000Z.json"]
    document = world.written()
    assert document["format"] == 2 and document["algorithm_version"] == "2"
    assert (document["companies_version"], document["resolutions_used"]) == (7, 0)
    assert document["companies_sha256"] == SHA
    assert (document["url_joins"], document["url_joins_unlike_title"], document["url_joins_refused"]) == (0, 0, 1)
    assert "url_joins 0" in report.line() and "url_joins_refused 1" in report.line()
    assert "companies_version 7" in report.line() and "resolutions_used 0" in report.line()
    assert parse_cluster_file(json.dumps(document).encode()).version == "2"


def test_the_same_inputs_give_the_same_bytes_and_a_second_run_changes_nothing(tmp_path):
    world = seeded(tmp_path)
    world.cluster()
    first = world.drive.get(f"raw/{cluster_path('2', AS_OF)}")
    world.build()
    assert world.cluster().ok and world.drive.get(f"raw/{cluster_path('2', AS_OF)}") == first


def test_no_company_list_at_all_is_a_run_with_version_zero_not_a_stop(tmp_path):
    missing = Scripted(CompanyListError(codes.COMPANY_LIST_MISSING))
    world = seeded(tmp_path, missing)
    assert world.cluster().ok and world.written()["companies_version"] == 0


@pytest.mark.parametrize(
    ("failure", "code"),
    [
        (CompanyListError(codes.COMPANY_LIST_INVALID), codes.COMPANY_LIST_INVALID),
        (CompanyListError(codes.COMPANY_LIST_ROLLED_BACK), codes.COMPANY_LIST_ROLLED_BACK),
        (CompanyListError(codes.COMPANY_LIST_DAMAGED), codes.COMPANY_LIST_DAMAGED),
        (OSError("down https://secret.example/x"), codes.COMPANY_LIST_UNAVAILABLE),
    ],
)
def test_a_list_that_exists_but_cannot_be_read_stops_the_run_and_writes_nothing(tmp_path, failure, code):
    world = seeded(tmp_path, Scripted(failure))
    report = world.cluster()
    assert report.rejected == {code: 1} and not report.ok and world.cluster_files() == []
    assert not (world.record.manifest_folder / "clusters.csv").exists() or not list(
        csv.DictReader((world.record.manifest_folder / "clusters.csv").read_text().splitlines())
    )
    assert "secret" not in report.line()


def wrapper(key: str, hours_before: float = 2) -> Article:
    seen = (AS_OF - timedelta(hours=hours_before)).isoformat(timespec="seconds")
    return Article(key, "wrapper", "Outlet", "A title", "", "", seen, "published", seen)


def test_only_the_windows_google_news_items_have_their_resolution_file_read(tmp_path):
    record = AreaStore(World(tmp_path).drive, "raw")
    resolved = Resolution("w1", STORY, "pub.example", "pub.example", True)
    record.put(resolution_path("w1"), resolved.to_bytes())
    record.put(resolution_path("old"), resolved.to_bytes())
    grouping = SymbolGrouping(Scripted(CompanyList(1, COMPANIES)), record)
    inputs = grouping.inputs((wrapper("w1"), wrapper("w2"), wrapper("old", hours_before=100)), AS_OF)
    assert inputs.resolutions_used == 1 and set(inputs.preparer.resolutions) == {
        "w1"
    }  # w2 unresolved, old out of window


def test_a_damaged_resolution_file_stops_the_run_with_one_code(tmp_path):
    record = AreaStore(World(tmp_path).drive, "raw")
    record.put(resolution_path("w1"), b"not json")
    grouping = SymbolGrouping(Scripted(CompanyList(1, COMPANIES)), record)
    with pytest.raises(GroupingBlocked) as caught:
        grouping.inputs((wrapper("w1"),), AS_OF)
    assert str(caught.value) == codes.RESOLUTION_UNREADABLE


def test_the_cluster_file_parser_accepts_formats_one_and_two_and_refuses_others(tmp_path):
    world = seeded(tmp_path)
    world.cluster()
    document = world.written()
    assert parse_cluster_file(json.dumps(document).encode()).version == "2"
    document["format"] = 1
    assert parse_cluster_file(json.dumps(document).encode()).window_hours == 48
    for bad in (0, 3, "2", None):
        document["format"] = bad
        with pytest.raises(ValueError):
            parse_cluster_file(json.dumps(document).encode())


def test_version_two_never_touches_version_one_files(tmp_path):
    plain = World(tmp_path)
    plain.add(item(HEADLINE, STORY, 8))
    assert plain.cluster().ok
    held = {f: plain.drive.get(f) for f in plain.cluster_files()}
    two = WorldTwo.__new__(WorldTwo)
    two.__dict__.update(plain.__dict__)
    two.build()
    assert two.cluster().ok
    assert {f: two.drive.get(f) for f in held} == held and any("/2/" in f for f in two.cluster_files())


def test_a_google_news_items_resolution_is_counted_in_the_file_that_used_it(tmp_path):
    world = WorldTwo.__new__(WorldTwo)
    world.record = Setup(tmp_path, kinds={FEED: WRAPPER})
    world.drive = world.record.drive
    world.build()
    world.add(item(HEADLINE, "https://wrap.svc.example/rss/a?oc=5", 8))
    [article] = world.run_object.source.candidates(AS_OF).articles
    resolved = Resolution(article.key, STORY, "pub.example", "pub.example", True)
    AreaStore(world.drive, "raw").put(resolution_path(article.key), resolved.to_bytes())
    assert world.cluster().ok and world.written()["resolutions_used"] == 1


def test_every_number_the_run_hands_the_file_is_written_under_its_own_name(tmp_path):
    from fno.ingestion.news.cluster.cluster import Clustering
    from fno.ingestion.news.cluster_record.cluster_file import cluster_file_bytes

    document = json.loads(cluster_file_bytes(Clustering(AS_OF, "2", (), 1, 2, 3, 4, 5, 6, 7, "c" * 64)))
    assert (document["url_joins"], document["url_joins_unlike_title"], document["url_joins_refused"]) == (3, 4, 5)
    assert (document["companies_version"], document["resolutions_used"]) == (6, 7)
    assert document["companies_sha256"] == "c" * 64
    assert (document["outside_window"], document["repeated_keys"], document["format"]) == (1, 2, 2)
    plain = json.loads(cluster_file_bytes(Clustering(AS_OF, "1", (), 0, 0)))
    assert plain["format"] == 1 and "url_joins" not in plain  # version 1 files are byte-for-byte as they were


def test_the_command_passes_the_algorithm_to_the_build_and_the_workflow_offers_it(monkeypatch):
    from pathlib import Path

    from fno.ingestion.news.cli import cmd_news_cluster

    seen = []

    class Done:
        ok, alert_text = True, staticmethod(lambda: "")

        @staticmethod
        def line():
            return "news cluster: ok"

    monkeypatch.setattr(
        "fno.ingestion.news.cluster_record.wiring.build_news_cluster",
        lambda algorithm="1": seen.append(algorithm) or type("R", (), {"run": lambda self, as_of: Done})(),
    )
    for chosen in ("1", "2"):
        assert cmd_news_cluster(type("A", (), {"as_of": None, "algorithm": chosen})(), out=lambda *_: None) == 0
    assert seen == ["1", "2"]
    text = (Path(__file__).parents[4] / ".github/workflows/news-cluster.yml").read_text()
    assert 'options: ["1", "2"]' in text and '--algorithm "${ALGORITHM:-1}"' in text and 'default: "1"' in text


def test_a_version_two_run_reads_its_previous_file_from_its_own_folder(tmp_path):
    earlier = AS_OF - timedelta(hours=1)
    world = seeded(tmp_path)
    world.cluster(earlier)
    v2_bytes = world.drive.get(f"raw/{cluster_path('2', earlier)}")
    other = json.loads(v2_bytes)  # a NEWER version 1 file with other ids: a version 2 run must not read it
    other |= {"format": 1, "algorithm_version": "1", "window_end": "20261027T114500Z"}
    other["clusters"] = [dict(c, cluster_id="f" * 64) for c in other["clusters"]]
    world.drive.put("raw/news/clusters/1/20261027T114500Z.json", json.dumps(other).encode())
    previous = world.run_object._previous(AS_OF)
    assert previous == parse_cluster_file(v2_bytes).clusters
    assert all(c.cluster_id != "f" * 64 for c in previous)


NEXT = AS_OF + timedelta(hours=1)


def second_run(tmp_path, companies):
    """A first version 2 file with list version 7 and bytes SHA, then the next window against `companies`."""
    world = seeded(tmp_path)
    assert world.cluster().ok
    world.companies = Scripted(companies)
    world.build()
    return world, world.cluster(NEXT)


def test_a_later_run_with_the_same_list_or_a_newer_one_goes_on_and_records_it(tmp_path):
    world, same = second_run(tmp_path, CompanyList(7, COMPANIES, SHA))
    assert same.ok
    world, newer = second_run(tmp_path / "n", CompanyList(8, COMPANIES, "b" * 64))
    assert newer.ok
    written = json.loads(world.drive.get(f"raw/{cluster_path('2', NEXT)}"))
    assert (written["companies_version"], written["companies_sha256"]) == (8, "b" * 64)


def test_an_older_list_than_the_last_file_used_stops_the_run_and_writes_nothing(tmp_path):
    world, report = second_run(tmp_path, CompanyList(6, COMPANIES, "b" * 64))
    assert report.rejected == {codes.COMPANY_LIST_ROLLED_BACK: 1} and not report.ok
    assert world.cluster_files() == ["raw/news/clusters/2/20261027T120000Z.json"]


def test_the_same_version_with_other_bytes_is_a_list_edited_in_place_and_stops_the_run(tmp_path):
    world, report = second_run(tmp_path, CompanyList(7, COMPANIES, "b" * 64))
    assert report.rejected == {codes.COMPANY_LIST_DAMAGED: 1} and not report.ok
    assert world.cluster_files() == ["raw/news/clusters/2/20261027T120000Z.json"]


def test_a_list_used_before_that_is_now_missing_stops_the_run_instead_of_becoming_version_zero(tmp_path):
    world, report = second_run(tmp_path, CompanyListError(codes.COMPANY_LIST_MISSING))
    assert report.rejected == {codes.COMPANY_LIST_MISSING: 1} and not report.ok


def test_after_a_run_with_no_list_a_list_that_appears_is_accepted(tmp_path):
    world = seeded(tmp_path, Scripted(CompanyListError(codes.COMPANY_LIST_MISSING)))
    assert world.cluster().ok
    world.companies = Scripted(CompanyList(1, COMPANIES, "b" * 64))
    world.build()
    assert world.cluster(NEXT).ok


def test_the_parser_reads_the_list_a_file_used_and_zero_for_a_file_that_has_none(tmp_path):
    world = seeded(tmp_path)
    world.cluster()
    found = parse_cluster_file(world.drive.get(f"raw/{cluster_path('2', AS_OF)}"))
    assert (found.companies_version, found.companies_sha256) == (7, SHA)
    document = world.written()
    for key in ("companies_version", "companies_sha256"):
        del document[key]
    document["format"] = 1
    none = parse_cluster_file(json.dumps(document).encode())
    assert (none.companies_version, none.companies_sha256) == (0, "")
