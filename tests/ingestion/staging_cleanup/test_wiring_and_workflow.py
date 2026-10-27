"""Story S1: what the composition root wires, and that the workflow is dormant and cannot overlap a stage."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml

from fno.ingestion.staging_cleanup import wiring
from fno.ingestion.staging_cleanup.proof import KeepForever, NseCopyProof
from fno.ingestion.staging_cleanup.trash import DriveStagingTrash
from fno.ingestion.storage.raw_store import LocalFolderStore

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "staging-cleanup.yml"


def built(monkeypatch, tmp_path, apply):
    drive = LocalFolderStore(tmp_path / "drive")
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env=None: drive)
    monkeypatch.setattr(wiring, "build_revision_archive", lambda env=None: SimpleNamespace(index=None))
    return wiring.build_staging_cleanup(apply, 10)


def test_without_apply_no_deleter_is_built_at_all(monkeypatch, tmp_path):
    assert built(monkeypatch, tmp_path, apply=False).trash is None


def test_with_apply_the_only_deleter_is_the_staging_trash(monkeypatch, tmp_path):
    assert isinstance(built(monkeypatch, tmp_path, apply=True).trash, DriveStagingTrash)


def test_nse_copies_have_the_proof_and_news_polls_are_kept_forever(monkeypatch, tmp_path):
    proofs = built(monkeypatch, tmp_path, apply=True).proofs
    assert isinstance(proofs["nse"], NseCopyProof) and isinstance(proofs["news"], KeepForever)
    assert set(proofs) == {"nse", "news"}


def test_the_proof_reads_the_record_area_and_the_staging_area_is_a_different_one(monkeypatch, tmp_path):
    cleanup = built(monkeypatch, tmp_path, apply=False)
    assert cleanup.proofs["nse"].record.area == "raw" and cleanup.staging.store.area == "staging"


def test_the_workflow_is_dispatch_only_report_only_by_default_and_serial_with_the_staging_workflow():
    flow = yaml.safe_load(WORKFLOW.read_text())
    triggers = flow.get("on", flow.get(True))
    assert list(triggers) == ["workflow_dispatch"]  # no schedule
    assert triggers["workflow_dispatch"]["inputs"]["apply"]["default"] is False
    assert flow["concurrency"]["group"] == "pipeline-staging" and flow["permissions"] == {"contents": "read"}
    text = WORKFLOW.read_text()
    assert "--source nse" in text and "news" not in text.split("jobs:")[1]  # news polls are not part of this run
    assert "git push" not in text and "git commit" not in text  # it commits nothing
