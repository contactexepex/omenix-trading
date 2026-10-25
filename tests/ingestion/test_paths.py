"""Repo-root path resolution must survive the fno/shared + fno/ingestion package layout.

Regression guard for the split: moving a module deeper changes `__file__` depth, so any
`Path(__file__).resolve().parents[N]` repo-root computation silently points at `fno/` instead of
the real root. The data-path roots must resolve to the repository root (where config.yaml lives),
never inside the `fno/` package.
"""
from __future__ import annotations

from pathlib import Path

from fno.ingestion.storage import wiring
from fno.shared.config import ROOT


def _repo_root() -> Path:
    # The directory that actually holds config.yaml + the fno/ and tests/ trees.
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "config.yaml").is_file() and (parent / "fno").is_dir():
            return parent
    raise AssertionError("repo root not found from the test file")


def test_shared_root_is_repo_root() -> None:
    root = _repo_root()
    assert root == ROOT
    assert (ROOT / "config.yaml").is_file()
    assert ROOT.name != "fno"  # not the package dir


def test_storage_repository_is_repo_root_not_package() -> None:
    root = _repo_root()
    assert root == wiring.REPOSITORY
    # must be the repo root, never inside the fno package
    assert wiring.REPOSITORY.name != "fno"
    assert not str(wiring.REPOSITORY).endswith("/fno")


def test_data_folders_hang_off_repo_root() -> None:
    root = _repo_root()
    assert root / "research" / "data" / "calendar" == wiring.CALENDAR_FOLDER
    assert root / "research" / "data" / "manifests" == wiring.MANIFEST_FOLDER
    # every research/ data root sits at the repo root, not under fno/
    for folder in (wiring.CALENDAR_FOLDER, wiring.PARTICIPANT_OI_EVIDENCE, wiring.PANEL_FOLDER):
        assert "/fno/research/" not in str(folder)
        assert str(folder).startswith(str(root) + "/research/")
