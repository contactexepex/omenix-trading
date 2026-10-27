"""P5b (judge 57 S1): the seven callers that ask `commit_failed` whether the committer's line is a failure, each with
the REAL lines. A failed commit must still end the run red (exit 1, alert, problem or False); a pushed commit and one
with nothing new must leave it exactly as it was. Without these, replacing `commit_failed` by "never failed" in any of
the seven stays green."""

from __future__ import annotations

from argparse import Namespace
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests

from fno.ingestion.circulars.episodes import OpenProblems
from fno.ingestion.circulars.job import CircularsJob
from fno.ingestion.close_read import cli as close_read_cli
from fno.ingestion.close_read import wiring as close_read_wiring
from fno.ingestion.flow_history import cli as flow_cli
from fno.ingestion.flow_history import wiring as flow_wiring
from fno.ingestion.fo_masters.job import FoMastersJob
from fno.ingestion.global_cues import preopen_cli
from fno.ingestion.preopen import record as preopen_record
from fno.ingestion.preopen.record import PreopenRecorder
from fno.ingestion.storage import repair_cli
from fno.ingestion.storage.manifest_commit import COMMIT_FAILED_ALERT, commit_failed
from tests.ingestion.commit_failure.real_lines import RealLines, real_lines

DAY = date(2026, 10, 1)


@pytest.fixture(scope="module")
def lines(tmp_path_factory) -> RealLines:
    return real_lines(tmp_path_factory.mktemp("real"))


class Recorder:
    def __init__(self, line):
        self.line = line

    def commit(self, what):
        return self.line


class Alerts:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return "alert sent"


def good_and_bad(lines):
    return [(lines.pushed, False), (lines.nothing, False), (lines.failed, True)]


def test_the_commit_failed_alert_text_is_not_itself_a_failure_line():
    """The alert is worded without the failure mark: fed back through a caller it is not a failed commit."""
    assert not commit_failed(COMMIT_FAILED_ALERT.format(what="data-librarian x"))


def test_circulars(lines, tmp_path):
    for line, failed in good_and_bad(lines):
        alerts, printed = Alerts(), []
        capture = MagicMock()
        capture.run.return_value = []
        job = CircularsJob(lambda: [], capture, [Recorder(line)], OpenProblems(tmp_path / "k.txt"), alerts,
                           lambda: None, "run-log", out=printed.append)  # fmt: skip
        assert job.run(DAY) == (1 if failed else 0)
        assert len(alerts.sent) == (1 if failed else 0)


def test_fo_masters(lines):
    calendar = MagicMock()
    calendar.session_kind.return_value = "regular"
    for line, failed in good_and_bad(lines):
        alerts = Alerts()
        job = FoMastersJob(calendar, [], Recorder(line), alerts, "run-log", out=lambda text: None)
        assert job.run(DAY) == (1 if failed else 0)
        assert len(alerts.sent) == (1 if failed else 0)


def test_close_read_commit(lines, monkeypatch):
    monkeypatch.setattr(close_read_wiring, "build_close_reader", lambda: MagicMock(run=lambda mode: 0))
    for line, failed in good_and_bad(lines):
        monkeypatch.setattr(close_read_wiring, "build_receipts_committer", lambda line=line: Recorder(line))
        code = close_read_cli.cmd_closes(Namespace(recheck=False, commit=True), out=lambda text: None)
        assert code == (1 if failed else 0)


def test_flows_table(lines, monkeypatch):
    monkeypatch.setattr(flow_wiring, "archived_days", lambda name: [])
    monkeypatch.setattr(flow_wiring, "entered_sessions", lambda name: [])
    result = MagicMock(entered=[], rewritten=[], waiting=[], problems=[])
    monkeypatch.setattr(flow_wiring, "build_flow_table_job", lambda name: MagicMock(run=lambda a, b: result))
    for line, failed in good_and_bad(lines):
        alerts = Alerts()
        monkeypatch.setattr(flow_wiring, "build_alerts", lambda alerts=alerts: alerts)
        monkeypatch.setattr(flow_wiring, "build_committers", lambda line=line: [Recorder(line)])
        code = flow_cli.cmd_flows_table(Namespace(dataset="participant-volume"), out=lambda text: None)
        assert code == (1 if failed else 0)
        assert len(alerts.sent) == (1 if failed else 0)


def test_repair_receipt(lines):
    repair = MagicMock()
    repair.receipt_for.return_value = SimpleNamespace(
        path="p", sha256="s", size=1, written_at="t", writer="w", run_id="r"
    )
    for line, failed in good_and_bad(lines):
        args = Namespace(path="p", writer="w", run_id="r", apply=True)
        code = repair_cli.cmd_receipt(args, out=lambda text: None, repair=repair, committer=Recorder(line))
        assert code == (1 if failed else 0)


def test_preopen_cli_receipts(lines):
    for line, failed in good_and_bad(lines):
        assert preopen_cli._committed(lambda text: None, lambda line=line: [Recorder(line)]) is (not failed)


def test_preopen_cli_a_committer_that_raises_is_not_committed_with_the_exact_text():
    printed = []

    def broken():
        raise requests.ConnectionError("down")

    assert preopen_cli._committed(printed.append, broken) is False
    assert printed == ["pre-open receipts NOT committed: ConnectionError"]


def recorder(committers=(), early=None, alerts=None):
    return PreopenRecorder(MagicMock(), MagicMock(), MagicMock(), MagicMock(), list(committers), alerts or Alerts(),
                           MagicMock(), early or Recorder(""), MagicMock(), out=lambda text: None)  # fmt: skip


def test_preopen_day_commit(lines):
    for line, failed in good_and_bad(lines):
        alerts = Alerts()
        assert recorder([Recorder(line)], alerts=alerts)._finish(DAY, []) == (1 if failed else 0)
        assert len(alerts.sent) == (1 if failed else 0)


def test_preopen_early_commit(lines, monkeypatch):
    monkeypatch.setattr(preopen_record, "early_file", lambda part, day: "f")
    monkeypatch.setattr(preopen_record, "early_row", lambda day, result: b"row")
    result = MagicMock(part="gift")
    for line, failed in good_and_bad(lines):
        problems = recorder(early=Recorder(line))._save_early(DAY, result)
        assert [p.kind for p in problems] == (["commit failed"] if failed else [])
