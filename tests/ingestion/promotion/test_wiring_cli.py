from fno.ingestion.cli import build_parser
from fno.ingestion.promotion import cli, wiring
from fno.ingestion.promotion.runs import StageReport
from fno.ingestion.storage.owner_token import DriveSignInRefused
from fno.ingestion.storage.raw_source import RawSourceUnavailable
from tests.ingestion.promotion.conftest import THURSDAY, SpyStore, moment

PATH = "nse/derivatives/participant-oi/2026/10/f.csv"


def test_the_wired_staging_area_can_only_write_under_staging(monkeypatch, tmp_path):
    from fno.ingestion.storage.raw_store import LocalFolderStore

    drive = SpyStore(LocalFolderStore(tmp_path))
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env: drive)
    area = wiring.build_staging_area({})
    area.stage("nse", PATH, b"x", moment(THURSDAY))
    assert drive.saved and all(p.startswith("staging/") for p in drive.saved)


def test_without_drive_settings_the_wiring_says_which_to_set(monkeypatch):
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env: None)
    try:
        wiring.build_staging_area({})
    except RuntimeError as exc:
        assert "FNO_GDRIVE_FOLDER_ID" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_the_cli_knows_stage_and_promote_for_the_promotable_datasets():
    args = build_parser().parse_args(["promote", "participant-oi", "--from", "2026-10-01"])
    assert args.func is cli.cmd_promote
    assert build_parser().parse_args(["stage", "fo-bhavcopy", "--from", "2026-10-01"]).func is cli.cmd_stage


class StubStager:
    def __init__(self, report=None, error=None):
        self.report, self.error = report, error

    def stage(self, start, end):
        if self.error:
            raise self.error
        return self.report


def run_stage(monkeypatch, stager):
    lines = []
    monkeypatch.setattr(wiring, "build_stager", lambda dataset: stager)
    args = build_parser().parse_args(["stage", "participant-oi", "--from", "2026-10-01"])
    return cli.cmd_stage(args, out=lines.append), "\n".join(lines)


def test_stage_exit_codes_and_messages(monkeypatch):
    assert run_stage(monkeypatch, StubStager(StageReport("d")))[0] == 0
    incomplete = StageReport("d", refused=[(THURSDAY, "HTTP 403")])
    assert run_stage(monkeypatch, StubStager(incomplete))[0] == 1
    code, text = run_stage(monkeypatch, StubStager(error=RawSourceUnavailable("down")))
    assert code == 1 and "stopped: down" in text
    code, text = run_stage(monkeypatch, StubStager(error=DriveSignInRefused("expired")))
    assert code == 1 and "Google refused the Drive upload sign-in" in text


class StubRecorder:
    def __init__(self):
        self.what = None

    def commit(self, what):
        self.what = what
        return "committed"


class StubAlerts:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return "alert sent"


def run_promote(monkeypatch, report, error=None):
    from fno.ingestion import composition
    from fno.ingestion.storage import wiring as storage_wiring

    class StubRun:
        def promote(self, start, end):
            if error:
                raise error
            return report

    recorder, alerts, lines = StubRecorder(), StubAlerts(), []
    monkeypatch.setattr(storage_wiring, "build_manifest_recorder", lambda: recorder)
    monkeypatch.setattr(composition, "build_alert_sender", lambda: alerts)
    monkeypatch.setattr(wiring, "build_promotion_run", lambda dataset, lag: StubRun())
    args = build_parser().parse_args(["promote", "participant-oi", "--from", "2026-10-01"])
    return cli.cmd_promote(args, out=lines.append), recorder, alerts, "\n".join(lines)


def test_promote_alerts_on_files_that_did_not_make_it_and_still_commits_manifest_rows(monkeypatch):
    from fno.ingestion.promotion.gate import Promotion, Verdict
    from fno.ingestion.promotion.runs import PromotionReport

    bad = PromotionReport("d", [(THURSDAY, Promotion(PATH, Verdict.REJECTED, ("f.csv: bad",)))])
    code, recorder, alerts, text = run_promote(monkeypatch, bad)
    assert code == 1 and recorder.what == "promote participant-oi"
    assert len(alerts.sent) == 1 and "f.csv: bad" in alerts.sent[0] and "NOT promoted" in alerts.sent[0]


def test_promote_that_promoted_everything_sends_no_alert(monkeypatch):
    from fno.ingestion.promotion.gate import Promotion, Verdict
    from fno.ingestion.promotion.runs import PromotionReport

    good = PromotionReport("d", [(THURSDAY, Promotion(PATH, Verdict.PROMOTED))])
    code, _, alerts, _ = run_promote(monkeypatch, good)
    assert code == 0 and alerts.sent == []


def test_promote_stops_on_a_refused_sign_in_but_still_commits(monkeypatch):
    code, recorder, _, text = run_promote(monkeypatch, None, error=DriveSignInRefused("expired"))
    assert code == 1 and "sign-in" in text and recorder.what is not None


def test_from_is_required_so_no_run_scans_all_history():
    import pytest

    for command in ("stage", "promote"):
        with pytest.raises(SystemExit):
            build_parser().parse_args([command, "participant-oi"])


def test_the_alert_names_at_most_five_problems_and_the_log_has_them_all(monkeypatch):
    from fno.ingestion.promotion.gate import Promotion, Verdict
    from fno.ingestion.promotion.runs import PromotionReport

    results = [
        (THURSDAY.replace(day=day), Promotion(PATH, Verdict.REJECTED, (f"reason {day}",))) for day in range(1, 9)
    ]
    code, _, alerts, text = run_promote(monkeypatch, PromotionReport("d", results))
    assert code == 1 and len(alerts.sent) == 1
    assert alerts.sent[0].count("reason") == cli.ALERT_LINES == 5
    assert text.count("rejected 2026-10-") == 8
