"""CF1 step 0: today's exit code of every caller that prints the committer's line, for each of the real lines. Written
BEFORE the change and passing on the unchanged code: the rows marked BUG pin the silent failure (a "NOT committed"
line leaves the exit code and the alerts as they are). Step 1 flips exactly those rows."""

from __future__ import annotations

from argparse import Namespace
from datetime import date

import pytest

from fno.ingestion import composition
from fno.ingestion.storage import librarian_cli, revisions_cli
from fno.ingestion.storage import wiring as storage_wiring
from fno.ingestion.storage.librarian import FillReport
from fno.ingestion.storage.raw_source import ParticipantOiSource, RawSourceUnavailable
from tests.ingestion.commit_failure.real_lines import RealLines, real_lines

D1, D2 = date(2026, 10, 1), date(2026, 10, 2)


@pytest.fixture(scope="module")
def lines(tmp_path_factory) -> RealLines:
    return real_lines(tmp_path_factory.mktemp("real"))


class Recorder:
    def __init__(self, line):
        self.line, self.what = line, None

    def commit(self, what):
        self.what = what
        return self.line


class Alerts:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return "alert sent"


# ---- data-librarian (run_librarian), both the finished and the stopped path ------------------------------------------


def librarian(line, *, complete=True, stopped=False):
    class Build:
        def fill(self, start, end):
            if stopped:
                raise RawSourceUnavailable("NSE down")
            report = FillReport("ds", start, end, sessions=1, present=1)
            if not complete:
                report.not_published.append(start)
            return report

    alerts, printed = Alerts(), []
    code = librarian_cli.run_librarian(
        lambda: Build(), alerts, Recorder(line), "data-librarian ds", D1, D2, out=printed.append
    )
    return code, alerts.sent


@pytest.mark.parametrize("line", ["pushed", "nothing"])
def test_librarian_a_good_commit_keeps_the_fill_exit_code(lines, line):
    assert librarian(getattr(lines, line)) == (0, [])
    assert librarian(getattr(lines, line), complete=False)[0] == 1
    assert librarian(getattr(lines, line), stopped=True)[0] == 1


def test_librarian_BUG_a_failed_commit_changes_nothing_in_the_finished_or_the_stopped_run(lines):
    assert librarian(lines.failed) == (0, [])  # BUG: green, no alert
    assert librarian(lines.failed, stopped=True)[0] == 1 and librarian(lines.failed, complete=False)[0] == 1


# ---- data-snapshot ------------------------------------------------------------------------------------------------


def snapshot(monkeypatch, line, *, error=None):
    class Taker:
        def take(self, day):
            if error:
                raise error
            return "archived"

    monkeypatch.setattr(storage_wiring, "build_manifest_recorder", lambda: Recorder(line))
    monkeypatch.setattr(storage_wiring, "build_snapshot_taker", lambda dataset: Taker())
    alerts = Alerts()
    monkeypatch.setattr(composition, "build_alert_sender", lambda: alerts)
    return librarian_cli.cmd_data_snapshot(Namespace(dataset="ds", day=D1)), alerts.sent


@pytest.mark.parametrize("line", ["pushed", "nothing"])
def test_snapshot_a_good_commit_keeps_the_exit_code(monkeypatch, lines, line):
    assert snapshot(monkeypatch, getattr(lines, line)) == (0, [])
    assert snapshot(monkeypatch, getattr(lines, line), error=ValueError("bad"))[0] == 1


def test_snapshot_BUG_a_failed_commit_changes_nothing(monkeypatch, lines):
    assert snapshot(monkeypatch, lines.failed) == (0, [])  # BUG: green, no alert
    assert snapshot(monkeypatch, lines.failed, error=ValueError("bad"))[0] == 1


# ---- data-revisions sweep ------------------------------------------------------------------------------------------


def revisions(monkeypatch, line, *, stopped=""):
    class Archive:
        stored, not_archived = [], []

    class Result:
        checked, unanswered = 3, {}

    Result.stopped = stopped
    monkeypatch.setattr(storage_wiring, "build_revision_archive", lambda: Archive())
    monkeypatch.setattr(storage_wiring, "build_manifest_recorder", lambda: Recorder(line))
    monkeypatch.setattr(
        storage_wiring, "build_session_calendar", lambda: type("C", (), {"is_session": lambda s, d: True})()
    )
    monkeypatch.setattr(storage_wiring, "build_revision_capturing_source", lambda source_type, archive: object())
    monkeypatch.setattr("fno.ingestion.storage.revision_source.sweep_revisions", lambda source, paths: Result())
    alerts = Alerts()
    monkeypatch.setattr(composition, "build_alert_sender", lambda: alerts)
    return revisions_cli._sweep(ParticipantOiSource, D1, D2), alerts.sent


@pytest.mark.parametrize("line", ["pushed", "nothing"])
def test_revisions_a_good_commit_keeps_the_exit_code(monkeypatch, lines, line):
    assert revisions(monkeypatch, getattr(lines, line)) == (0, [])
    assert revisions(monkeypatch, getattr(lines, line), stopped="NSE down")[0] == 1


def test_revisions_BUG_a_failed_commit_changes_nothing(monkeypatch, lines):
    assert revisions(monkeypatch, lines.failed) == (0, [])  # BUG: green, no alert
    assert revisions(monkeypatch, lines.failed, stopped="NSE down")[0] == 1


# ---- promote -------------------------------------------------------------------------------------------------------


def promote(monkeypatch, line, *, rejected=False):
    from fno.ingestion.cli import build_parser
    from fno.ingestion.promotion import cli, wiring
    from fno.ingestion.promotion.gate import Promotion, Verdict
    from fno.ingestion.promotion.runs import PromotionReport

    verdict = Verdict.REJECTED if rejected else Verdict.PROMOTED
    report = PromotionReport("d", [(D1, Promotion("nse/derivatives/participant-oi/2026/10/f.csv", verdict, ("bad",)))])

    class Run:
        def promote(self, start, end):
            return report

    alerts = Alerts()
    monkeypatch.setattr(storage_wiring, "build_manifest_recorder", lambda: Recorder(line))
    monkeypatch.setattr(composition, "build_alert_sender", lambda: alerts)
    monkeypatch.setattr(wiring, "build_promotion_run", lambda dataset, lag: Run())
    args = build_parser().parse_args(["promote", "participant-oi", "--from", "2026-10-01"])
    return cli.cmd_promote(args, out=lambda text: None), alerts.sent


@pytest.mark.parametrize("line", ["pushed", "nothing"])
def test_promote_a_good_commit_keeps_the_exit_code(monkeypatch, lines, line):
    assert promote(monkeypatch, getattr(lines, line)) == (0, [])
    code, sent = promote(monkeypatch, getattr(lines, line), rejected=True)
    assert code == 1 and len(sent) == 1


def test_promote_BUG_a_failed_commit_changes_nothing(monkeypatch, lines):
    assert promote(monkeypatch, lines.failed) == (0, [])  # BUG: green, no alert
    assert promote(monkeypatch, lines.failed, rejected=True)[0] == 1


# ---- the intraday recorder's report -------------------------------------------------------------------------------


@pytest.mark.parametrize("line", ["pushed", "nothing"])
def test_intraday_a_good_commit_keeps_the_exit_code(lines, line):
    from fno.ingestion.intraday.cli import report
    from fno.ingestion.intraday.recorder import SlotOutcome

    assert report([SlotOutcome("good", "09:30", lines=[getattr(lines, line)])]) == 0
    assert report([SlotOutcome("failed", "09:30", lines=[getattr(lines, line)])]) == 1


def test_intraday_BUG_a_failed_commit_changes_nothing(lines):
    from fno.ingestion.intraday.cli import report
    from fno.ingestion.intraday.recorder import SlotOutcome

    assert report([SlotOutcome("good", "09:30", lines=[lines.failed])]) == 0  # BUG: green
    assert report([SlotOutcome("failed", "09:30", lines=[lines.failed])]) == 1


# ---- nsdl-backfill (a hand command) ----------------------------------------------------------------------------------


def nsdl(monkeypatch, line, *, failed=None):
    from fno.ingestion.flow_history import cli, wiring
    from fno.ingestion.storage import data_wiring

    class Result:
        saved, rows, empty, skipped = [1], 5, [], []

    Result.failed = failed or {}
    alerts = Alerts()
    monkeypatch.setattr(wiring, "build_nsdl_backfill", lambda: type("B", (), {"run": lambda s, months: Result()})())
    monkeypatch.setattr(wiring, "build_alerts", lambda: alerts)
    monkeypatch.setattr(data_wiring, "build_receipt_committer", lambda: Recorder(line))
    return cli.cmd_nsdl_backfill(
        Namespace(through=date(2019, 3, 31)), out=lambda text: None, today=date(2026, 10, 27)
    ), alerts.sent


@pytest.mark.parametrize("line", ["pushed", "nothing"])
def test_nsdl_a_good_commit_keeps_the_exit_code(monkeypatch, lines, line):
    assert nsdl(monkeypatch, getattr(lines, line)) == (0, [])
    assert nsdl(monkeypatch, getattr(lines, line), failed={date(2019, 1, 31): "x"})[0] == 1


def test_nsdl_BUG_a_failed_commit_changes_nothing(monkeypatch, lines):
    assert nsdl(monkeypatch, lines.failed) == (0, [])  # BUG: green, no alert
    assert nsdl(monkeypatch, lines.failed, failed={date(2019, 1, 31): "x"})[0] == 1
