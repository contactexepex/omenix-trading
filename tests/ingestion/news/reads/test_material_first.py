"""NP8: the read pass reads material headlines first, degrades loudly on a broken private file and writes a note."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.companies.model import Company, CompanyList, CompanyListSource
from fno.ingestion.news.companies.parse import CompanyListError
from fno.ingestion.news.materiality.terms import MaterialityError, parse_terms
from fno.ingestion.news.reads import queue as queue_module
from fno.ingestion.news.reads.limits import MAX_RECORD_READS, RESOLVE_READS, SCORE_READS
from fno.ingestion.news.reads.order import MaterialFirst, NewestFirst, Scored
from fno.ingestion.news.reads.pass_note import FOLDER, PassNote, PassNotes, parse_note, path_id
from fno.ingestion.news.reads.plan import ReadPlanner
from fno.ingestion.news.reads.read_file import key_of_path
from fno.ingestion.news.reads.run import ReadPass
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.wrapper_index import WRAPPERS_FILE
from fno.ingestion.news.tagging.dictionary import NameDictionary
from fno.ingestion.news.tagging.tagger import Tagger
from fno.ingestion.news.write_once import WriteOnceWriter
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import AreaStore
from tests.ingestion.news.reads.helpers import RULES, TODAY, World, wrapper_item

SHA_C, SHA_M = "c" * 64, "d" * 64
MOMENT = datetime(2026, 10, 27, 9, 30, 0, tzinfo=UTC)


class Companies(CompanyListSource):
    def __init__(self, result):
        self.result = result

    def companies(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class Terms:
    def __init__(self, result):
        self.result = result

    def terms(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def companies(version=2, sha=SHA_C) -> CompanyList:
    return CompanyList(version, (Company("ZZPB", "Zzpub"),), sha)


def terms(version=3, sha=SHA_M):
    return parse_terms(b'{"format":1,"terms":[{"pattern":"zzpub","weight":1}]}', version, sha)


class Setup(World):
    """A read World whose pass has a planner over scripted private files and a real pass-note writer."""

    def __init__(self, tmp_path, company=None, material=None):
        super().__init__(tmp_path)
        self.company, self.material = company or Companies(companies()), material or Terms(terms())
        self.seconds = 0

    def read_pass(self, reads_file: str = "reads.csv") -> ReadPass:
        base = super().read_pass(reads_file)
        record = AreaStore(self.drive, "raw")
        store = DataStore(self.drive, "raw", self.record.receipts, "news-read", "run-1")
        writer = WriteOnceWriter(record, store, NewsManifest(self.record.manifest_folder, "read-passes.csv"), path_id)
        self.notes = PassNotes(record, writer)
        base.planner, base.notes, base.now = (
            ReadPlanner(self.company, self.material, self.notes),
            self.notes,
            self.tick,
        )
        return base

    def tick(self) -> datetime:
        """A clock that moves one second per pass, as real passes do: a note's name is its second."""
        self.seconds += 1
        return MOMENT + timedelta(seconds=self.seconds - 1)

    def note_files(self) -> list[str]:
        folder = self.drive.folder / "raw" / FOLDER
        return sorted(p.name for p in folder.rglob("*.json")) if folder.exists() else []

    def mixed(self) -> None:
        """Three Google News items (not material, resolved) and three publisher items naming the company (material)."""
        self.add(wrapper_item(1), wrapper_item(2), wrapper_item(3))
        self.add_publisher(7, 8, 9)
        self.resolve_all()


def asked_publishers(world) -> int:
    return sum(url.startswith("https://pub.example") for url in world.fetcher.asked)


def test_material_articles_are_read_before_the_others_when_the_pages_are_fewer_than_the_articles(tmp_path):
    world = Setup(tmp_path)
    world.mixed()
    report = world.read(pages=3)
    assert report.ok and report.order == "material_first" and asked_publishers(world) == 3
    assert (report.counts["scored"], report.counts["material"], report.counts["material_asked"]) == (6, 3, 3)
    assert "order material_first" in report.line() and "material_asked 3" in report.line()


def test_without_a_planner_the_pass_reads_newest_first_as_it_always_did(tmp_path):
    world = Setup(tmp_path)
    world.mixed()
    plain = World.read_pass(world)
    report = plain.run(TODAY, True, 3, 900.0)
    assert report.order is None and "order" not in report.line() and report.counts["asked"] == 3
    assert report.counts["scored"] == 0 and world.note_files() == []


def test_never_configured_is_green_newest_first_and_writes_no_note(tmp_path):
    missing_c, missing_m = (
        Companies(CompanyListError(codes.COMPANY_LIST_MISSING)),
        Terms(MaterialityError(codes.MATERIALITY_MISSING)),
    )
    world = Setup(tmp_path, missing_c, missing_m)
    world.mixed()
    report = world.read(pages=3)
    assert report.ok and report.order == "newest_first" and "order newest_first" in report.line()
    assert world.note_files() == [] and report.counts["asked"] == 3


def test_a_material_first_pass_with_apply_writes_one_note_of_counts_and_versions_and_a_probe_none(tmp_path):
    world = Setup(tmp_path)
    world.mixed()
    assert world.read(apply=False, pages=3).ok and world.note_files() == []
    report = world.read(pages=3)
    (name,) = world.note_files()
    data = (world.drive.folder / "raw" / FOLDER / name).read_bytes()
    note = parse_note(data)
    assert name == "20261027T093001Z.json" and report.ok  # the probe before it took :00 and wrote nothing
    assert (note.order, note.scored, note.material, note.asked) == ("material_first", 6, 3, 3)
    assert (note.materiality_version, note.materiality_sha256) == (3, SHA_M)
    assert (note.companies_version, note.companies_sha256) == (2, SHA_C)
    assert b"Zzpub" not in data and b"zzpub" not in data and b"ZZPB" not in data and b"https" not in data
    manifest = (world.record.manifest_folder / "read-passes.csv").read_text()
    assert path_id(f"{FOLDER}/{name}") in manifest
    assert world.read(pages=3).ok and len(world.note_files()) == 2  # the next pass, the next second, the next note


@pytest.mark.parametrize(
    ("company", "material", "code"),
    [
        (Companies(CompanyListError(codes.COMPANY_LIST_INVALID)), None, codes.COMPANY_LIST_INVALID),
        (Companies(OSError("down https://secret.example")), None, codes.COMPANY_LIST_UNAVAILABLE),
        (None, Terms(MaterialityError(codes.MATERIALITY_INVALID)), codes.MATERIALITY_INVALID),
        (None, Terms(OSError("down https://secret.example")), codes.MATERIALITY_UNAVAILABLE),
    ],
)
def test_a_private_file_that_exists_but_cannot_be_used_degrades_to_newest_first_red_with_no_note_and_reads_go_on(
    tmp_path, company, material, code
):
    world = Setup(tmp_path, company, material)
    world.mixed()
    report = world.read(pages=3)
    assert report.rejected == {code: 1} and not report.ok and report.order == "newest_first"
    assert report.counts["asked"] == 3 and report.pages["written"] == 3 and world.note_files() == []
    assert "secret" not in report.line() and code in report.line()


def test_a_degraded_pass_leaves_the_pin_where_the_last_good_note_put_it(tmp_path):
    world = Setup(tmp_path)
    world.mixed()
    assert world.read(pages=3).ok
    (first,) = world.note_files()
    cases = [
        (Terms(terms(version=2)), codes.MATERIALITY_ROLLED_BACK),  # older than the note's 3
        (Terms(terms(version=3, sha="e" * 64)), codes.MATERIALITY_DAMAGED),  # edited in place
        (Terms(MaterialityError(codes.MATERIALITY_MISSING)), codes.MATERIALITY_MISSING),  # used, and now gone
    ]
    for bad, code in cases:
        world.material = bad
        report = world.read(pages=3)
        assert report.rejected == {code: 1} and report.order == "newest_first"
    for bad, code in (
        (Companies(companies(version=1)), codes.COMPANY_LIST_ROLLED_BACK),
        (Companies(companies(sha="f" * 64)), codes.COMPANY_LIST_DAMAGED),
        (Companies(CompanyListError(codes.COMPANY_LIST_MISSING)), codes.COMPANY_LIST_MISSING),
    ):
        world.material, world.company = Terms(terms()), bad
        assert world.read(pages=3).rejected == {code: 1}
    assert world.note_files() == [first]  # no degraded pass wrote a note, so the pin never moved
    world.company = Companies(companies())
    assert world.read(pages=3).ok  # the good files are still accepted against the last good note


def test_a_newer_version_of_either_file_is_accepted_and_recorded(tmp_path):
    world = Setup(tmp_path)
    world.mixed()
    assert world.read(pages=3).ok
    world.material, world.company = Terms(terms(version=4, sha="a" * 64)), Companies(companies(version=5, sha="b" * 64))
    later = datetime(2026, 10, 27, 10, 0, 0, tzinfo=UTC)
    pass_ = world.read_pass()
    pass_.now = lambda: later
    assert pass_.run(TODAY, True, 3, 900.0).ok
    note = parse_note((world.drive.folder / "raw" / FOLDER / "20261027T100000Z.json").read_bytes())
    assert (note.materiality_version, note.companies_version) == (4, 5)


def test_a_damaged_last_note_degrades_with_its_own_code(tmp_path):
    world = Setup(tmp_path)
    world.mixed()
    folder = world.drive.folder / "raw" / FOLDER
    folder.mkdir(parents=True)
    (folder / "20261027T000000Z.json").write_bytes(b"not json")
    report = world.read(pages=3)
    assert (
        report.rejected == {codes.PASS_NOTE_UNREADABLE: 1}
        and report.order == "newest_first"
        and world.note_files() == ["20261027T000000Z.json"]
    )


def test_the_record_reads_are_one_budget_and_the_ranking_counts_what_it_could_not_reach(tmp_path, monkeypatch):
    assert SCORE_READS + RESOLVE_READS == MAX_RECORD_READS
    world = Setup(tmp_path)
    world.mixed()
    monkeypatch.setattr(queue_module, "SCORE_READS", 4)
    report = world.read(pages=80)
    assert report.counts["scored"] == 4 and report.counts["unexamined"] == 2 and not report.rejected.get("x")


def test_google_news_items_left_without_a_resolution_read_are_counted_and_a_publisher_item_still_follows(
    tmp_path, monkeypatch
):
    world = Setup(tmp_path)
    world.mixed()
    monkeypatch.setattr(queue_module, "RESOLVE_READS", 2)
    report = world.read(pages=80)
    assert report.counts["resolve_reads"] == 2 and report.counts["resolve_reads_exhausted"] == 1
    assert report.counts["asked"] == 5 and asked_publishers(world) == 3


def test_a_google_news_item_not_resolved_yet_is_counted_and_costs_no_resolution_read(tmp_path):
    world = Setup(tmp_path)
    world.add(wrapper_item(1))
    world.add_publisher(7)
    report = world.read(pages=80)
    assert report.counts["unresolved"] == 1 and report.counts["resolve_reads"] == 0 and report.counts["asked"] == 1


def test_an_outlet_we_may_not_read_is_skipped_in_the_material_first_path_too(tmp_path):
    from fno.ingestion.news.resolve.model import RESOLVED, Resolved

    world = Setup(tmp_path)
    world.add(wrapper_item(1))
    world.resolver.answers["https://wrap.svc.example/rss/articles/CBMi0001?oc=5"] = Resolved(
        RESOLVED, "https://unlisted.example/a"
    )
    world.resolve_all()
    report = world.read(pages=80)
    assert report.counts["unlisted"] == 1 and world.fetcher.asked == []


def scored(key: str, title: str) -> Scored:
    return Scored(key, title, "Pub Daily", "", False)


def test_the_order_puts_material_first_and_keeps_newest_first_inside_each_tier():
    tagger = Tagger(NameDictionary(companies()))
    order = MaterialFirst(tagger, terms())
    newest_first = [scored("a", "Plain a"), scored("b", "Zzpub b"), scored("c", "Plain c"), scored("d", "Zzpub d")]
    ranked, material = order.rank(newest_first)
    assert [s.key for s in ranked] == ["b", "d", "a", "c"] and material == 2
    assert order.rank([]) == ([], 0)
    plain, none = NewestFirst().rank(newest_first)
    assert plain == newest_first and none == 0
    assert order.rank([scored("e", "Zzpub and Zzpub")])[1] == 1


def test_an_article_naming_no_company_or_two_is_not_material_whatever_its_weight():
    two = CompanyList(1, (Company("ZZPB", "Zzpub"), Company("ZZQN", "Zzqueen")))
    order = MaterialFirst(Tagger(NameDictionary(two)), terms())
    assert order.rank([scored("a", "Zzpub and Zzqueen"), scored("b", "Nothing here")])[1] == 0
    assert order.rank([scored("c", "Zzpub")])[1] == 1


def test_the_pass_note_is_counts_and_versions_only():
    note = PassNote("material_first", 1, 2, 3, 4, "m" * 64, 5, "c" * 64)
    document = json.loads(note.to_bytes())
    assert set(document) == {
        "format", "order", "scored", "material", "asked", "materiality_version", "materiality_sha256",
        "companies_version", "companies_sha256",
    }  # fmt: skip
    assert parse_note(note.to_bytes()) == note
    for bad in (b"[]", b"{}", json.dumps({**document, "extra": 1}).encode(), b"\xff"):
        with pytest.raises(ValueError):
            parse_note(bad)


def test_the_workflow_commits_the_pass_notes_manifest_and_receipts():
    from pathlib import Path

    text = (Path(__file__).parents[4] / ".github/workflows/news-read-pages.yml").read_text()
    assert "EXTRA_MANIFESTS: research/data/manifests/news/read-passes.csv" in text
    assert "receipts/raw/news/read-passes" in text


__all__ = ["RULES", "WRAPPERS_FILE", "key_of_path"]


def test_two_passes_in_the_same_second_with_other_counts_are_a_conflict_never_an_overwrite(tmp_path):
    world = Setup(tmp_path)
    world.mixed()
    first = world.read_pass()
    first.now = lambda: MOMENT
    assert first.run(TODAY, True, 3, 900.0).ok
    second = world.read_pass()
    second.now = lambda: MOMENT
    report = second.run(TODAY, True, 3, 900.0)
    assert report.rejected == {codes.READ_CONFLICT: 1} and world.note_files() == ["20261027T093000Z.json"]


def test_the_pin_is_checked_against_the_newest_note_not_the_first(tmp_path):
    world = Setup(tmp_path)
    world.mixed()
    assert world.read(pages=3).ok  # a note with materiality 3
    world.material = Terms(terms(version=4, sha="a" * 64))
    assert world.read(pages=3).ok  # a later note with materiality 4
    world.material = Terms(terms(version=3))  # the first note's file again: older than the newest
    report = world.read(pages=3)
    assert report.rejected == {codes.MATERIALITY_ROLLED_BACK: 1}


def test_a_note_manifest_row_that_is_not_whole_is_counted_and_nothing_is_read_or_written(tmp_path):
    """Judge 108 B1 (1): the read-passes manifest is checked like the reads manifest."""
    world = Setup(tmp_path)
    world.mixed()
    (world.record.manifest_folder / "read-passes.csv").write_text(
        "date,article_id,status,sha256,size_bytes\nnot,a,whole row\n"
    )
    report = world.read(pages=3)
    assert report.rejected[codes.MANIFEST_ROW_SKIPPED] == 1 and world.fetcher.asked == [] and world.note_files() == []


def test_a_torn_note_manifest_stops_the_pass_before_any_request(tmp_path):
    """Judge 108 B1 (2): a manifest that ends in a torn line stops an applied pass before it writes anything."""
    world = Setup(tmp_path)
    world.mixed()
    row = "2026-10-27," + "a" * 64 + ",recorded," + "b" * 64 + ",10"
    (world.record.manifest_folder / "read-passes.csv").write_text("date,article_id,status,sha256,size_bytes\n" + row)
    report = world.read(pages=3)
    assert report.rejected[codes.MANIFEST_BROKEN] == 1 and world.fetcher.asked == [] and world.read_files() == []
