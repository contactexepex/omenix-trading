"""The gate's later versions land in the real A11 revisions area (RevisionArchive on local folders), once each."""

from __future__ import annotations

from datetime import timedelta

from fno.ingestion.promotion.checks import SchemaCheck
from fno.ingestion.promotion.gate import PromotionGate, Verdict
from fno.ingestion.promotion.revision_sink import ArchiveRevisionSink
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.manifest_folder import ManifestFolder
from fno.ingestion.storage.raw_source import ParticipantOiSource
from fno.ingestion.storage.raw_store import LocalFolderStore
from fno.ingestion.storage.revisions import RevisionArchive, RevisionIndex
from tests.ingestion.promotion.conftest import THURSDAY, moment

SOURCE = ParticipantOiSource
PATH, NAME = SOURCE.path_for(THURSDAY), SOURCE.filename_for(THURSDAY)


def test_a_later_staged_version_is_saved_in_the_revisions_area_with_an_index_row(tmp_path, staging_store, record_store):
    revisions = LocalFolderStore(tmp_path / "revisions")
    index = RevisionIndex(tmp_path / "index", [SOURCE])
    archive = RevisionArchive(record_store, revisions, index, ManifestFolder(tmp_path / "manifests"))
    staging = StagingArea(staging_store)
    gate = PromotionGate(staging, record_store, "nse", [SchemaCheck(lambda n, d: None)], ArchiveRevisionSink(archive))
    later = moment(THURSDAY) + timedelta(hours=5)
    staging.stage("nse", PATH, b"first", moment(THURSDAY))
    staging.stage("nse", PATH, b"second", later)

    assert gate.promote(PATH, THURSDAY, NAME).revisions == 1
    (row,) = index.for_path(PATH)
    assert revisions.get(row.revision_path) == b"second" and record_store.get(PATH) == b"first"
    assert row.found_at == later  # when the version was fetched, not when the gate ran

    again = gate.promote(PATH, THURSDAY, NAME)  # a second run keeps nothing twice
    assert again.verdict is Verdict.ALREADY_RECORDED and again.revisions == 0 and len(index.for_path(PATH)) == 1
