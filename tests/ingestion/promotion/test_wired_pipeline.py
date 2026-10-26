"""The real composition root end to end on local folders: the same source tag on both sides, the librarian's rules from
the repository's calendar, and the owner's `promotion.max_lag_days` reaching the gate (judge 1, #9)."""

from __future__ import annotations

from datetime import date

import pytest

from fno.ingestion.cli import build_parser
from fno.ingestion.promotion import cli, wiring
from fno.ingestion.promotion.gate import Verdict
from fno.ingestion.storage.raw_source import ParticipantOiSource
from fno.ingestion.storage.raw_store import LocalFolderStore
from tests.ingestion.promotion.conftest import FakeNse, RecordingSink, SpyStore
from tests.ingestion.promotion.samples import participant_file

SOURCE = ParticipantOiSource
SESSION = date(2026, 10, 21)  # a Wednesday session in the repository's calendar (20 Oct is a holiday)


class StubArchive:
    def __init__(self):
        self.sink = RecordingSink()

    def capture(self, path, published, found_at=None):
        return object() if self.sink.capture(path, published.data, found_at) else None


@pytest.fixture
def wired(monkeypatch, tmp_path):
    drive = SpyStore(LocalFolderStore(tmp_path / "drive"))
    record = SpyStore(LocalFolderStore(tmp_path / "record"))
    source = FakeNse({SOURCE.path_for(SESSION): participant_file(SESSION)})
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env: drive)
    monkeypatch.setattr(wiring, "build_owner_drive_store", lambda env: record)
    monkeypatch.setattr(wiring, "build_revision_archive", lambda env: StubArchive())
    monkeypatch.setattr(wiring, "build_nse_source", lambda source_type: source)
    wiring.build_stager("participant-oi").stage(SESSION, SESSION)
    return drive, record


def test_what_build_stager_stages_build_promotion_run_promotes_with_no_window_by_default(wired):
    drive, record = wired
    assert all(path.startswith("staging/") for path in drive.saved)
    report = wiring.build_promotion_run("participant-oi", env={}).promote(SESSION, SESSION)
    assert report.days(Verdict.PROMOTED) == [SESSION] and record.get(SOURCE.path_for(SESSION))


def test_a_configured_window_reaches_the_wired_gate(wired):
    _, record = wired
    report = wiring.build_promotion_run("participant-oi", max_lag_days=1, env={}).promote(SESSION, SESSION)
    assert report.days(Verdict.REJECTED) == [SESSION] and "after" in report.problems()[0]
    assert record.saved == []


def test_the_wired_checks_name_the_librarians_rules_and_the_window_only_when_set():
    names = lambda lag: [c.name for c in wiring.checks_for("fo-bhavcopy", lambda n, d: None, None, {}, lag)]  # noqa: E731
    assert names(None) == ["session", "exception", "schema", "content day"]
    assert names(3) == ["session", "exception", "schema", "content day", "freshness"]


class Capture:
    def __init__(self):
        self.lag = "not called"

    def __call__(self, dataset, lag):
        self.lag = lag
        raise cli.DriveSignInRefused("stopped here")


@pytest.mark.parametrize(
    ("config", "expected"), [("promotion:\n  max_lag_days: 4\n", 4), ("promotion:\n  max_lag_days: null\n", None)]
)
def test_cmd_promote_passes_the_config_key_to_the_wiring(monkeypatch, tmp_path, config, expected):
    from fno.ingestion.storage import wiring as storage_wiring
    from tests.ingestion.promotion.test_wiring_cli import StubRecorder

    path = tmp_path / "config.yaml"
    path.write_text(config, encoding="utf-8")
    capture = Capture()
    monkeypatch.setattr(wiring, "build_promotion_run", capture)
    monkeypatch.setattr(storage_wiring, "build_manifest_recorder", StubRecorder)
    args = build_parser().parse_args(["--config", str(path), "promote", "participant-oi", "--from", "2026-10-01"])
    assert cli.cmd_promote(args, out=lambda line: None) == 1
    assert capture.lag == expected


def test_the_wired_gate_sends_a_later_version_to_the_revision_archive(monkeypatch, wired, tmp_path):
    from datetime import UTC, datetime

    archive = StubArchive()
    monkeypatch.setattr(wiring, "build_revision_archive", lambda env: archive)
    drive, _ = wired
    later = participant_file(SESSION).replace(b"2026", b"2026 ", 1)  # other bytes, same session and layout
    wiring.build_staging_area({}).stage("nse", SOURCE.path_for(SESSION), later, datetime(2026, 12, 1, tzinfo=UTC))
    report = wiring.build_promotion_run("participant-oi", env={}).promote(SESSION, SESSION)
    assert report.revisions == 1 and len(archive.sink.offered) == 1
