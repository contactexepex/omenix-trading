"""NP3c: the comparison run is read only, prints counts only and stops on an unusable company list."""

from __future__ import annotations

from pathlib import Path

from fno.ingestion.news import codes
from fno.ingestion.news.cli import cmd_news_compare
from fno.ingestion.news.cluster_record.grouping import SymbolGrouping
from fno.ingestion.news.companies.model import CompanyList
from fno.ingestion.news.companies.parse import CompanyListError
from fno.ingestion.news.compare.run import ComparisonRun
from fno.ingestion.storage.raw_store import AreaStore
from tests.ingestion.news.cluster_record.helpers import AS_OF
from tests.ingestion.news.cluster_record.test_version_two_run import Scripted, seeded
from tests.ingestion.news.tagging.helpers import COMPANIES

ROOT = Path(__file__).resolve().parents[4]


def comparison(world, companies) -> ComparisonRun:
    record = AreaStore(world.drive, "raw")
    return ComparisonRun(world.run_object.source, SymbolGrouping(companies, record))


def files(world) -> dict:
    return {
        str(p.relative_to(world.drive.folder)): p.read_bytes() for p in world.drive.folder.rglob("*") if p.is_file()
    }


def manifests(world) -> dict:
    return {p.name: p.read_bytes() for p in world.record.manifest_folder.rglob("*") if p.is_file()}


def test_the_comparison_prints_the_five_lines_of_counts(tmp_path):
    world = seeded(tmp_path)
    report = comparison(world, Scripted(CompanyList(7, COMPANIES))).run(AS_OF)
    lines = report.line().splitlines()
    assert report.ok and [line.split(":")[0] for line in lines] == ["v1", "v2", "v1 vs v2", "v2 inputs", "tags"]
    assert lines[0].startswith("v1: clustered 3, clusters 3") and "singletons" in lines[0] and "sizes 2-2:0" in lines[0]
    assert (
        "companies_version 7" in lines[3]
        and "url_joins_unlike_title 0" in lines[3]
        and "url_joins_refused 1" in lines[3]
    )
    assert lines[4].startswith("tags: articles 3,")


def test_the_comparison_writes_nothing_to_the_drive_or_the_manifests_and_names_no_story(tmp_path):
    world = seeded(tmp_path)
    before, before_manifests = files(world), manifests(world)
    text = comparison(world, Scripted(CompanyList(7, COMPANIES))).run(AS_OF).line()
    assert files(world) == before and manifests(world) == before_manifests
    assert "Nifty" not in text and "https://" not in text and "pub.example" not in text


def test_a_company_list_that_exists_but_cannot_be_read_stops_the_comparison_with_its_code(tmp_path):
    world = seeded(tmp_path)
    for failure, code in (
        (CompanyListError(codes.COMPANY_LIST_INVALID), codes.COMPANY_LIST_INVALID),
        (OSError("down https://secret.example"), codes.COMPANY_LIST_UNAVAILABLE),
    ):
        report = comparison(world, Scripted(failure)).run(AS_OF)
        assert report.rejected == {code: 1} and not report.ok and "secret" not in report.line()
        assert report.line() == f"\nnews compare-clusterings stopped, {code} 1"


def test_no_list_at_all_still_compares_with_version_zero(tmp_path):
    world = seeded(tmp_path)
    report = comparison(world, Scripted(CompanyListError(codes.COMPANY_LIST_MISSING))).run(AS_OF)
    assert report.ok and "companies_version 0" in report.line() and "tagged 0" in report.line()


def test_the_command_prints_the_lines_and_exits_zero_or_one_and_never_a_traceback(monkeypatch):
    class Fake:
        def __init__(self, ok):
            self.ok = ok

        def line(self):
            return "v1: ok"

    out = []
    for ok, expected in ((True, 0), (False, 1)):
        monkeypatch.setattr(
            "fno.ingestion.news.compare.wiring.build_comparison",
            lambda ok=ok: type("R", (), {"run": lambda self, as_of: Fake(ok)})(),
        )
        assert cmd_news_compare(type("A", (), {"as_of": None})(), out=out.append) == expected

    def boom():
        raise ValueError("leaks https://secret.example/x")

    monkeypatch.setattr("fno.ingestion.news.compare.wiring.build_comparison", boom)
    assert cmd_news_compare(type("A", (), {"as_of": None})(), out=out.append) == 1
    assert out[-1] == f"news compare-clusterings stopped: {codes.UNEXPECTED} ValueError"


def test_the_comparison_has_no_way_to_write():
    for module in ("run", "wiring"):
        text = (ROOT / f"fno/ingestion/news/compare/{module}.py").read_text()
        for word in ("ClusterWriter", "DataStore", "WriteOnceWriter", ".put(", "batch_receipt_writer", "alert"):
            assert word not in text.split('"""', 2)[2], (module, word)


def test_the_workflow_is_manual_read_only_and_commits_and_alerts_nothing():
    text = (ROOT / ".github/workflows/news-compare-clusterings.yml").read_text()
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert "workflow_dispatch" in body and "schedule:" not in body
    assert "contents: read" in body and "contents: write" not in body
    for word in ("commit_news_record", "git push", "FNO_SLACK_BOT_TOKEN", "--apply"):
        assert word not in body, word
