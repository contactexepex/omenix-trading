"""Composition root of the staging cleanup (story S1): the only place that picks the concrete stores.

What it wires, and why the deleter cannot reach the Record: the cleanup is handed (1) a `StagingArea` over an
`AreaStore` on `staging`, which can list and read staging and nothing else; (2) READ-ONLY views of the Record (the `raw`
area) and of the revisions index, used only to PROVE a staged copy is promoted; and (3) in apply mode only, a
`DriveStagingTrash`. That class has no general delete: it accepts a staged copy's parts (source, archive path, fetch
stamp), builds `staging/...` itself, and hard-refuses any path not strictly inside `staging/`, again at the last step
before Drive. In report-only mode no deleter is built at all. The limit is in this code, not in credentials (the one
Drive credential is shared, as for the promotion gate), and it is pinned by tests with a Record path as the plant.

News polls are not removed: the Record keeps an article's fields, not the raw poll, so a promoted poll is not lossless
to drop. They have `KeepForever` until the owner decides; changing that is one entry in `proofs()`."""

from __future__ import annotations

import os

from fno.ingestion.news.feeds import PrivateFeedLists
from fno.ingestion.news.fetcher import SOURCE as NEWS_TAG
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.planner import ArticlePlanner
from fno.ingestion.news.wiring import CONFIG_AREA, POLL_LOG_FOLDER
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.promotion.wiring import NSE_TAG, STAGING_AREA
from fno.ingestion.staging_cleanup.cleanup import StagingCleanup
from fno.ingestion.staging_cleanup.news_proof import NewsPollProof
from fno.ingestion.staging_cleanup.proof import NseCopyProof, PromotedProof
from fno.ingestion.staging_cleanup.trash import DriveStagingTrash
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.revisions import RevisionArchive
from fno.ingestion.storage.wiring import (
    OWNER_UPLOAD_SETTINGS,
    RAW_AREA,
    build_owner_drive,
    build_revision_archive,
)

NEEDS_DRIVE = "set {settings} to clean the staging area"


class ArchiveRevisionHolds:
    """Read-only: whether the revisions index lists a version of a path with a SHA-256."""

    def __init__(self, archive: RevisionArchive):
        self.archive = archive

    def holds(self, path: str, sha256: str) -> bool:
        return any(r.sha256 == sha256 for r in self.archive.index.for_path(path))


def proofs(record: AreaStore, archive: RevisionArchive, kinds: dict[str, str]) -> dict[str, PromotedProof]:
    news = NewsPollProof(kinds, ArticlePlanner(record), NewsManifest(POLL_LOG_FOLDER))
    return {NSE_TAG: NseCopyProof(record, ArchiveRevisionHolds(archive)), NEWS_TAG: news}


def build_staging_cleanup(apply: bool, limit: int, env=os.environ) -> StagingCleanup:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    staging = StagingArea(AreaStore(drive, STAGING_AREA))
    record = AreaStore(drive, RAW_AREA)
    trash = DriveStagingTrash(drive) if apply else None
    kinds = PrivateFeedLists(AreaStore(drive, CONFIG_AREA)).kinds_ever_listed()
    return StagingCleanup(staging, proofs(record, build_revision_archive(env), kinds), trash, limit=limit)
