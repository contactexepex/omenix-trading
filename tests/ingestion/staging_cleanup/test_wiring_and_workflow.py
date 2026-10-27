"""Story S1: what the composition root wires, and that the workflow is dormant and cannot overlap a stage."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from fno.ingestion.staging_cleanup import wiring
from fno.ingestion.staging_cleanup.news_proof import NewsPollProof
from fno.ingestion.staging_cleanup.proof import NseCopyProof
from fno.ingestion.staging_cleanup.trash import DriveStagingTrash
from fno.ingestion.storage.manifest_folder import ManifestFolder
from fno.ingestion.storage.raw_store import LocalFolderStore

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "staging-cleanup.yml"


KINDS = {"feed-01": "publisher"}


def built(monkeypatch, tmp_path, apply, sources=("nse", "news")):
    drive = LocalFolderStore(tmp_path / "drive")
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env=None: drive)
    monkeypatch.setattr(wiring, "build_revision_archive", lambda env=None: SimpleNamespace(index=None))
    monkeypatch.setattr(wiring, "PrivateFeedLists", lambda store: SimpleNamespace(kinds_ever_listed=lambda: KINDS))
    monkeypatch.setattr(wiring, "POLL_LOG_FOLDER", tmp_path / "manifests")
    monkeypatch.setattr(wiring, "build_manifest_folder", lambda: ManifestFolder(tmp_path / "manifests"))
    return wiring.build_staging_cleanup(apply, 10, sources)


def test_without_apply_no_deleter_is_built_at_all(monkeypatch, tmp_path):
    assert built(monkeypatch, tmp_path, apply=False).trash is None


def test_with_apply_the_only_deleter_is_the_staging_trash(monkeypatch, tmp_path):
    assert isinstance(built(monkeypatch, tmp_path, apply=True).trash, DriveStagingTrash)


def test_nse_copies_and_news_polls_each_have_their_own_proof_and_nothing_else_is_removable(monkeypatch, tmp_path):
    proofs = built(monkeypatch, tmp_path, apply=True).proofs
    assert isinstance(proofs["nse"], NseCopyProof) and isinstance(proofs["news"], NewsPollProof)
    assert proofs["news"].kinds == KINDS and set(proofs) == {"nse", "news"}


def test_the_news_proof_is_built_with_the_wrapper_index_so_the_cleanup_consults_it(monkeypatch, tmp_path):
    """judges 85, 86: without this, the S1 index-row check could be silently off in production."""
    proof = built(monkeypatch, tmp_path, apply=True).proofs["news"]
    assert proof.wrappers.log.path.name == "wrappers.csv" and proof.manifest.log.path.name == "articles.csv"


def test_the_news_proof_cannot_be_built_without_an_index():
    with pytest.raises(TypeError):
        NewsPollProof(KINDS, None, None)  # the index is required: a missing one must not turn the check off


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


def test_the_deleters_staging_root_is_the_area_the_gate_stages_into():
    from fno.ingestion.promotion.wiring import STAGING_AREA
    from fno.ingestion.staging_cleanup.trash import STAGING_ROOT

    assert STAGING_ROOT == STAGING_AREA


def test_a_news_free_run_never_reads_the_feed_list(monkeypatch, tmp_path):
    def broken():
        raise RuntimeError("feed list unreadable")

    drive = LocalFolderStore(tmp_path / "drive")
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env=None: drive)
    monkeypatch.setattr(wiring, "build_revision_archive", lambda env=None: SimpleNamespace(index=None))
    monkeypatch.setattr(wiring, "build_manifest_folder", lambda: ManifestFolder(tmp_path / "manifests"))
    monkeypatch.setattr(wiring, "PrivateFeedLists", lambda store: SimpleNamespace(kinds_ever_listed=broken))
    cleanup = wiring.build_staging_cleanup(False, 10, ["nse"])
    assert set(cleanup.proofs) == {"nse"}


def test_the_fingerprints_adapter_finds_a_record_files_row_by_its_file_name(tmp_path):
    from datetime import date

    from fno.ingestion.storage.manifest_folder import Fingerprint
    from fno.ingestion.storage.source_lists import RAW_SOURCES

    source = RAW_SOURCES[0]
    path = source.path_for(date(2026, 10, 1))
    manifests = ManifestFolder(tmp_path / "manifests")
    manifests.record(source, Fingerprint.of(source, path, b"bytes"))
    adapter = wiring.ArchiveFingerprints(manifests)
    assert adapter.sha256_of(path) == Fingerprint.of(source, path, b"bytes").sha256
    assert adapter.sha256_of("nowhere/x.csv") is None
