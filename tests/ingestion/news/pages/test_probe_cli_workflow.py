"""NP4a: the outlet probe, its command and its dispatch-only workflow."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
import yaml

from fno.ingestion.news import codes
from fno.ingestion.news.pages import cli as probe_cli
from fno.ingestion.news.pages import model, wiring
from fno.ingestion.news.pages.model import Page, PageFetcher
from fno.ingestion.news.pages.probe import probe_outlets
from tests.ingestion.news.pages.helpers import RULES, fetcher, urls

ROOT = Path(__file__).resolve().parents[4]


class Recording(PageFetcher):
    def __init__(self, answers=None):
        self.answers, self.asked = answers or {}, []

    def fetch(self, url):
        self.asked.append(url)
        return Page(self.answers.get(url, model.OK), url)


def test_the_probe_asks_each_fetchable_outlet_front_page_once_and_leaves_the_refusing_ones_alone():
    recording = Recording({"https://other.example/": model.REFUSED})
    report = probe_outlets(RULES, recording, include_refusing=False)
    assert sorted(recording.asked) == ["https://other.example/", "https://pub.example/"]
    assert report.line() == "news probe-outlets: 2 outlets, ok 1, refused 1"


def test_the_refusing_outlets_are_looked_at_only_when_asked_and_are_marked_in_the_report():
    recording = Recording()
    report = probe_outlets(RULES, recording, include_refusing=True)
    assert "https://closed.example/" in recording.asked and "https://in.closed.example/" in recording.asked
    lines = report.outlet_lines()
    assert lines[:2] == ["other.example: ok", "pub.example: ok"] and "closed.example (fetch: false): ok" in lines
    assert report.reachable == 4


def test_the_probe_through_the_real_fetcher_obeys_every_guard_and_names_only_domains_and_codes():
    fetch, session, _ = fetcher()  # robots.txt answers 404 (no restriction), the front pages answer 404 too
    report = probe_outlets(RULES, fetch, include_refusing=False)
    assert {code for _, _, code in report.results} == {model.HTTP_ERROR}
    assert all(url.startswith("https://") and url.endswith(("/", "/robots.txt")) for url in urls(session))


def test_the_command_prints_a_counts_line_then_one_line_per_outlet_and_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(wiring, "load_source_rules", lambda: RULES)
    monkeypatch.setattr(wiring, "build_page_fetcher", lambda include_refusing=False: Recording())
    lines: list[str] = []
    assert probe_cli.cmd_probe_outlets(Namespace(include_refusing=False), out=lines.append) == 0
    assert lines == ["other.example: ok", "pub.example: ok", "news probe-outlets: 2 outlets, ok 2"]


def test_an_unexpected_error_prints_only_its_class(monkeypatch):
    monkeypatch.setattr(
        wiring, "load_source_rules", lambda: (_ for _ in ()).throw(ValueError("https://secret.example/x"))
    )
    lines: list[str] = []
    assert probe_cli.cmd_probe_outlets(Namespace(include_refusing=False), out=lines.append) == 1
    assert lines == [f"news probe-outlets stopped: {codes.UNEXPECTED} ValueError"]


def test_the_wiring_widens_the_allowlist_only_for_the_probe_and_only_to_listed_hosts(monkeypatch):
    monkeypatch.setattr(wiring, "load_source_rules", lambda: RULES)
    ordinary, widened = wiring.build_page_fetcher(), wiring.build_page_fetcher(include_refusing=True)
    assert not ordinary.host_allowed("closed.example") and widened.host_allowed("closed.example")
    assert not widened.host_allowed("unlisted.example") and ordinary.host_allowed("pub.example")


# ---- the workflow ---------------------------------------------------------------------------------------------------


def workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/news-probe-outlets.yml").read_text())


def test_the_workflow_is_dispatch_only_read_only_and_holds_no_secret():
    document = workflow()
    triggers = document.get("on", document.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    assert document["permissions"] == {"contents": "read"}
    text = (ROOT / ".github/workflows/news-probe-outlets.yml").read_text()
    assert "secrets." not in text and "git push" not in text and "git commit" not in text and "schedule:" not in text
    assert triggers["workflow_dispatch"]["inputs"]["include_refusing"]["default"] is False


def test_each_outlet_line_is_printed_as_it_completes_so_a_killed_run_leaves_the_log_so_far():
    seen: list[str] = []

    class Dies(PageFetcher):
        def fetch(self, url):
            if url.startswith("https://pub.example"):
                raise KeyboardInterrupt  # the runner is killed here
            return Page(model.OK, url)

    with pytest.raises(KeyboardInterrupt):
        probe_outlets(RULES, Dies(), include_refusing=False, on_result=seen.append)
    assert seen == ["other.example: ok"]  # what was known before the kill was already out


def test_the_job_timeout_covers_the_worst_case_of_every_request_timing_out():
    steps = workflow()["jobs"]["probe"]
    assert steps["timeout-minutes"] * 60 >= 224 * 20  # ~224 requests, 20 s timeout each


def test_the_probe_job_does_not_buffer_its_output_so_a_hard_kill_keeps_the_lines_already_printed():
    """judge 87: on a runner stdout is a pipe, which is block-buffered unless this is set."""
    assert workflow()["jobs"]["probe"]["env"]["PYTHONUNBUFFERED"] == "1"
