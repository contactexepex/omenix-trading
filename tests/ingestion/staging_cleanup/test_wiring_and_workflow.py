"""Story S1: what the composition root wires, and that the workflow is dormant and cannot overlap a stage."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml

from fno.ingestion.staging_cleanup import wiring
from fno.ingestion.staging_cleanup.news_proof import NewsPollProof
from fno.ingestion.staging_cleanup.proof import NseCopyProof
from fno.ingestion.staging_cleanup.trash import DriveStagingTrash
from fno.ingestion.storage.raw_store import LocalFolderStore

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "staging-cleanup.yml"


KINDS = {"feed-01": "publisher"}


def built(monkeypatch, tmp_path, apply):
    drive = LocalFolderStore(tmp_path / "drive")
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env=None: drive)
    monkeypatch.setattr(wiring, "build_revision_archive", lambda env=None: SimpleNamespace(index=None))
    monkeypatch.setattr(wiring, "PrivateFeedLists", lambda store: SimpleNamespace(kinds_ever_listed=lambda: KINDS))
    monkeypatch.setattr(wiring, "POLL_LOG_FOLDER", tmp_path / "manifests")
    return wiring.build_staging_cleanup(apply, 10)


def test_without_apply_no_deleter_is_built_at_all(monkeypatch, tmp_path):
    assert built(monkeypatch, tmp_path, apply=False).trash is None


def test_with_apply_the_only_deleter_is_the_staging_trash(monkeypatch, tmp_path):
    assert isinstance(built(monkeypatch, tmp_path, apply=True).trash, DriveStagingTrash)


def test_nse_copies_and_news_polls_each_have_their_own_proof_and_nothing_else_is_removable(monkeypatch, tmp_path):
    proofs = built(monkeypatch, tmp_path, apply=True).proofs
    assert isinstance(proofs["nse"], NseCopyProof) and isinstance(proofs["news"], NewsPollProof)
    assert proofs["news"].kinds == KINDS and set(proofs) == {"nse", "news"}


def test_the_proof_reads_the_record_area_and_the_staging_area_is_a_different_one(monkeypatch, tmp_path):
    cleanup = built(monkeypatch, tmp_path, apply=False)
    assert cleanup.proofs["nse"].record.area == "raw" and cleanup.staging.store.area == "staging"


def test_the_workflow_is_dispatch_only_report_only_by_default_and_each_job_serial_with_its_writer():
    flow = yaml.safe_load(WORKFLOW.read_text())
    triggers = flow.get("on", flow.get(True))
    assert list(triggers) == ["workflow_dispatch"]  # no schedule
    assert triggers["workflow_dispatch"]["inputs"]["apply"]["default"] is False
    assert flow["permissions"] == {"contents": "read"}
    groups = {name: job["concurrency"]["group"] for name, job in flow["jobs"].items()}
    assert groups == {"nse-staging": "pipeline-staging", "news-staging": "news-record"}
    text = WORKFLOW.read_text()
    assert "--source nse" in text and "--source news" in text
    assert "git push" not in text and "git commit" not in text  # it commits nothing
