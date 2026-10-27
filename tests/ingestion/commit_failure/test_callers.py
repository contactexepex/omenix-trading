"""CF1: every caller that prints the committer's line, for each of the REAL lines. A commit that pushed, and one with
nothing new to commit, leave every exit code exactly as it was (no live run turns red). A "NOT committed" line now
ends the run at least red with exactly one alert. Step 0 of the story pinned the old, silent behaviour on the
unchanged code; this file keeps the good-commit rows and flips only the failed-commit rows."""

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


def test_librarian_a_failed_commit_is_red_with_one_alert_in_the_finished_and_the_stopped_run(lines):
    for kwargs in ({}, {"stopped": True}, {"complete": False}):
        code, sent = librarian(lines.failed, **kwargs)
        assert code == 1 and len(sent) == 1 and "NOT committed" in sent[0] and "data-librarian ds" in sent[0]


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


def test_snapshot_a_failed_commit_is_red_with_one_alert(monkeypatch, lines):
    for error in (None, ValueError("bad")):
        code, sent = snapshot(monkeypatch, lines.failed, error=error)
        assert code == 1 and len(sent) == 1 and "data-snapshot ds" in sent[0]


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


def test_revisions_a_failed_commit_is_red_with_one_alert(monkeypatch, lines):
    for stopped in ("", "NSE down"):
        code, sent = revisions(monkeypatch, lines.failed, stopped=stopped)
        assert code == 1 and len(sent) == 1 and "data-revisions sweep" in sent[0]


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


def test_promote_a_failed_commit_is_red_with_its_own_alert(monkeypatch, lines):
    code, sent = promote(monkeypatch, lines.failed)
    assert code == 1 and len(sent) == 1 and "promote participant-oi" in sent[0]
    code, sent = promote(
        monkeypatch, lines.failed, rejected=True
    )  # the rejected-files alert and the commit alert are two problems
    assert code == 1 and len(sent) == 2


# ---- the intraday recorder's report -------------------------------------------------------------------------------


@pytest.mark.parametrize("line", ["pushed", "nothing"])
def test_intraday_a_good_commit_keeps_the_exit_code(lines, line):
    from fno.ingestion.intraday.cli import report
    from fno.ingestion.intraday.recorder import SlotOutcome

    alerts = Alerts()
    assert report([SlotOutcome("good", "09:30", lines=[getattr(lines, line)])], alerts) == 0
    assert report([SlotOutcome("failed", "09:30", lines=[getattr(lines, line)])], alerts) == 1 and alerts.sent == []


def test_intraday_a_failed_commit_on_any_mark_is_red_with_one_alert(lines):
    from fno.ingestion.intraday.cli import report
    from fno.ingestion.intraday.recorder import SlotOutcome

    alerts = Alerts()
    marks = [SlotOutcome("good", "09:30", lines=[lines.pushed]), SlotOutcome("good", "09:45", lines=[lines.failed]),
             SlotOutcome("good", "10:00", lines=[lines.failed])]  # fmt: skip
    assert report(marks, alerts) == 1 and len(alerts.sent) == 1  # two failed commits, still one alert per run
    assert report([SlotOutcome("failed", "09:30", lines=[lines.failed])], alerts) == 1


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


def test_nsdl_a_failed_commit_is_red_with_one_alert(monkeypatch, lines):
    code, sent = nsdl(monkeypatch, lines.failed)
    assert code == 1 and len(sent) == 1 and "nsdl-backfill" in sent[0]
    code, sent = nsdl(
        monkeypatch, lines.failed, failed={date(2019, 1, 31): "x"}
    )  # the failed months and the commit: two problems
    assert code == 1 and len(sent) == 2


# ---- the two paths that leave early: promote with a refused sign-in, and intraday rv -------------------------


def test_promote_with_a_refused_sign_in_is_red_anyway_and_a_failed_commit_adds_its_alert(monkeypatch, lines):
    from fno.ingestion.cli import build_parser
    from fno.ingestion.promotion import cli, wiring
    from fno.ingestion.storage.owner_token import DriveSignInRefused

    def refuse(dataset, lag):
        raise DriveSignInRefused("expired")

    results = {}
    for name in ("pushed", "failed"):
        alerts = Alerts()
        monkeypatch.setattr(storage_wiring, "build_manifest_recorder", lambda name=name: Recorder(getattr(lines, name)))
        monkeypatch.setattr(composition, "build_alert_sender", lambda alerts=alerts: alerts)
        monkeypatch.setattr(wiring, "build_promotion_run", refuse)
        args = build_parser().parse_args(["promote", "participant-oi", "--from", "2026-10-01"])
        results[name] = (cli.cmd_promote(args, out=lambda text: None), alerts.sent)
    assert results["pushed"] == (1, [])
    assert (
        results["failed"][0] == 1
        and len(results["failed"][1]) == 1
        and "promote participant-oi" in results["failed"][1][0]
    )


def intraday_rv(monkeypatch, settled_lines):
    from fno.ingestion import composition as comp
    from fno.ingestion.intraday import cli, wiring
    from fno.shared import config

    class Recorder:
        def settle_day(self, day):
            return settled_lines

    alerts = Alerts()
    monkeypatch.setattr(config, "load_app_config", lambda path: {})
    monkeypatch.setattr(comp, "build_alert_sender", lambda: alerts)
    monkeypatch.setattr(wiring, "build_intraday_recorder", lambda cfg, folder: Recorder())
    args = Namespace(intraday_cmd="rv", day=None, config=None)
    return cli.cmd_intraday(args), alerts.sent


@pytest.mark.parametrize("line", ["pushed", "nothing"])
def test_intraday_rv_a_good_commit_stays_green(monkeypatch, lines, line):
    assert intraday_rv(monkeypatch, ["settled", getattr(lines, line)]) == (0, [])


def test_intraday_rv_a_failed_commit_is_red_with_one_alert(monkeypatch, lines):
    code, sent = intraday_rv(monkeypatch, ["settled", lines.failed])
    assert code == 1 and len(sent) == 1 and "intraday rv" in sent[0]


# ---- the intraday sync's foreign-staged refusal (judge 55 F2) ----------------------------------------


def foreign_staged_line(alerts):
    """The REAL line, made by the real GitLedgerSync with a checkout that has another writer's file staged."""
    from fno.ingestion.intraday.sync import GitLedgerSync

    class Committer:
        label = "intraday ledger"

        def foreign_staged(self):
            return ["research/data/other.csv"]

    return GitLedgerSync(Committer(), alerts).commit("x")


def test_the_real_foreign_staged_line_is_the_sync_alerting_once_and_naming_the_refusal():
    from fno.ingestion.intraday.sync import refused_for_foreign_staging

    sync_alerts = Alerts()
    line = foreign_staged_line(sync_alerts)
    assert refused_for_foreign_staging(line) and len(sync_alerts.sent) == 1


def test_a_foreign_staged_refusal_makes_the_intraday_run_red_without_a_second_alert(lines):
    from fno.ingestion.intraday.cli import report
    from fno.ingestion.intraday.recorder import SlotOutcome

    refusal = foreign_staged_line(Alerts())
    ours = Alerts()
    assert report([SlotOutcome("good", "09:30", lines=[refusal])], ours) == 1 and ours.sent == []
    assert (
        report(
            [SlotOutcome("good", "09:30", lines=[lines.pushed]), SlotOutcome("good", "09:45", lines=[refusal])], ours
        )
        == 1
    )
    assert ours.sent == []


def test_a_refusal_and_a_failed_commit_in_one_run_alert_once_for_the_commit_only(lines):
    from fno.ingestion.intraday.cli import report
    from fno.ingestion.intraday.recorder import SlotOutcome

    ours = Alerts()
    outcomes = [
        SlotOutcome("good", "09:30", lines=[foreign_staged_line(Alerts())]),
        SlotOutcome("good", "09:45", lines=[lines.failed]),
    ]
    assert report(outcomes, ours) == 1 and len(ours.sent) == 1 and "intraday recorder" in ours.sent[0]


def test_intraday_rv_with_a_foreign_staged_refusal_is_red_without_a_second_alert(monkeypatch, lines):
    code, sent = intraday_rv(monkeypatch, ["settled", foreign_staged_line(Alerts())])
    assert code == 1 and sent == []


def test_the_refusal_mark_is_the_whole_phrase_and_matches_neither_the_committer_failure_nor_a_push(lines):
    from fno.ingestion.intraday.sync import refused_for_foreign_staging

    assert not refused_for_foreign_staging(lines.failed) and not refused_for_foreign_staging(lines.pushed)
    assert not refused_for_foreign_staging(lines.nothing) and not refused_for_foreign_staging("x NOT pulled: dry run")
