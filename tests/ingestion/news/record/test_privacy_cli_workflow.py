"""P2b2: nothing but hash ids and counts leaves Drive (manifest, receipts, the printed line, DEBUG logs), the command's
exit code and alert, and the workflow that must stay manual."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import yaml

from fno.ingestion.cli import build_parser
from fno.ingestion.news import cli as news_cli
from tests.ingestion.news.article.samples import rss, rss_item
from tests.ingestion.news.fakes import MARK_HEADLINE, MARK_HOST, MARK_PATH, MARK_QUERY
from tests.ingestion.news.record.helpers import POLL_AT, Setup

ROOT = Path(__file__).resolve().parents[4]
LINK = f"https://{MARK_HOST}/{MARK_PATH}/a?q={MARK_QUERY}"


def everything_public(s, report) -> str:
    texts = [s.manifest_text(), report.line()]
    texts += [f.read_text() for f in (s.receipts.folder).rglob("*") if f.is_file()]
    return "\n".join(texts)


def test_no_title_url_or_query_reaches_the_manifest_receipts_or_the_report(tmp_path, caplog):
    s = Setup(tmp_path)
    caplog.set_level(logging.DEBUG)
    s.stage(rss(rss_item(title=MARK_HEADLINE, link=LINK), rss_item(title=None, link=LINK + "2")))
    s.stage(b"<!DOCTYPE " + LINK.encode() + b">", at=POLL_AT + timedelta(hours=1))
    report = s.promote()
    public = everything_public(s, report) + caplog.text
    for marker in (MARK_HEADLINE, MARK_HOST, MARK_PATH, MARK_QUERY):
        assert marker not in public
    assert MARK_HEADLINE in s.drive.get(s.record_files()[0]).decode()  # it lives in private Drive only


def test_the_command_prints_one_line_and_alerts_only_when_something_stayed_staged(tmp_path, monkeypatch):
    s = Setup(tmp_path)
    s.stage(rss(rss_item(), rss_item(title=None)))
    alerts, printed = [], []
    monkeypatch.setattr("fno.ingestion.news.record.wiring.build_news_promotion", lambda: s.gate)
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender", lambda: type("A", (), {"send": alerts.append})()
    )
    args = build_parser().parse_args(["news", "promote", "--from", "2026-10-27", "--to", "2026-10-27"])
    assert news_cli.cmd_news_promote(args, out=printed.append) == 1
    assert printed[0].endswith("item_missing_title 1") and len(alerts) == 1
    s.build()
    alerts.clear()
    clean = Setup(tmp_path / "clean")
    clean.stage(rss(rss_item()))
    monkeypatch.setattr("fno.ingestion.news.record.wiring.build_news_promotion", lambda: clean.gate)
    assert news_cli.cmd_news_promote(args, out=printed.append) == 0 and alerts == []


def test_an_unexpected_error_prints_only_its_class(monkeypatch):
    def boom():
        raise ValueError(f"leaks {LINK}")

    printed = []
    monkeypatch.setattr("fno.ingestion.news.record.wiring.build_news_promotion", boom)
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender", lambda: type("A", (), {"send": lambda s, m: ""})()
    )
    args = build_parser().parse_args(["news", "promote", "--from", "2026-10-27"])
    assert news_cli.cmd_news_promote(args, out=printed.append) == 1
    assert printed[0] == "news promote stopped: unexpected_error ValueError" and MARK_HOST not in "".join(printed)


def test_from_is_required():
    import pytest

    with pytest.raises(SystemExit):
        build_parser().parse_args(["news", "promote"])


def test_the_workflow_has_no_schedule_and_commits_only_its_own_paths():
    text = (ROOT / ".github/workflows/news-promote.yml").read_text()
    flow = yaml.safe_load(text)
    assert set(flow[True]) == {"workflow_dispatch"}  # YAML reads `on` as True; no schedule key
    assert 'git add "$MANIFEST" "$RECEIPTS"' in text and "receipts/raw/news" in text
    assert "research/data/manifests/news/articles.csv" in text and "--no-verify" not in text


def _steps():
    (job,) = yaml.safe_load((ROOT / ".github/workflows/news-promote.yml").read_text()).get("jobs").values()
    return {step.get("name", ""): step for step in job["steps"]}


def test_the_promote_step_may_fail_without_stopping_the_commit_and_the_commit_has_no_outcome_condition():
    """judge 48 S3: good rows and receipts are committed even when the promotion exits 1; then the run fails."""
    steps = _steps()
    promote = steps["Promote staged polls through the article gate"]
    commit = steps["Commit the news manifest and receipts (only when the manifest is whole)"]
    final = next(s for n, s in steps.items() if n.startswith("Fail the run"))
    assert promote["continue-on-error"] is True
    assert (
        commit["if"] == "${{ !inputs.dry_run }}" and "steps." not in commit["if"] and "continue-on-error" not in commit
    )
    assert "steps.promote.outcome != 'success'" in final["if"] and final["run"] == "exit 1"


def test_the_commit_step_runs_the_manifest_guard_and_skips_only_a_broken_manifest():
    """The guard judges the file, never promote's outcome: a rejection still commits, a torn file never does."""
    commit = _steps()["Commit the news manifest and receipts (only when the manifest is whole)"]
    run = commit["run"]
    assert commit["if"] == "${{ !inputs.dry_run }}" and "steps." not in run
    assert "if python -m fno news check-manifest; then" in run and run.index("check-manifest") < run.index("git add")
    assert "git push origin HEAD:main" in run and "else" in run


def _check(tmp_path, monkeypatch, torn):
    from tests.ingestion.news.record.helpers import Setup

    s = Setup(tmp_path)
    s.stage(rss(rss_item()))
    s.promote()
    if torn:
        path = s.manifest_folder / "articles.csv"
        path.write_text(path.read_text().rstrip("\n")[:-40])
    monkeypatch.setattr("fno.ingestion.news.wiring.POLL_LOG_FOLDER", s.manifest_folder)
    printed = []
    return news_cli.cmd_news_check_manifest(None, out=printed.append), printed


def test_check_manifest_passes_a_whole_file_and_an_absent_one(tmp_path, monkeypatch):
    assert _check(tmp_path, monkeypatch, torn=False) == (0, ["news manifest: whole"])
    monkeypatch.setattr("fno.ingestion.news.wiring.POLL_LOG_FOLDER", tmp_path / "nothing")
    out = []
    assert news_cli.cmd_news_check_manifest(None, out=out.append) == 0


def test_check_manifest_refuses_a_torn_file_and_a_not_whole_row(tmp_path, monkeypatch):
    assert _check(tmp_path / "a", monkeypatch, torn=True) == (1, ["news manifest: manifest_broken"])
    s_path = tmp_path / "b" / "repo" / "manifests" / "articles.csv"
    s_path.parent.mkdir(parents=True)
    s_path.write_text("date,article_id,status,sha256,size_bytes\n2026-10-27,abc,recorded,def,1\n")
    monkeypatch.setattr("fno.ingestion.news.wiring.POLL_LOG_FOLDER", s_path.parent)
    assert news_cli.cmd_news_check_manifest(None, out=lambda line: None) == 1
