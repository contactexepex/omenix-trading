"""Composition root of the staging cleanup (story S1): the only place that picks the concrete stores.

What it wires, and why the deleter cannot reach the Record: the cleanup is handed (1) a `StagingArea` over an
`AreaStore` on `staging`, which can list and read staging and nothing else; (2) READ-ONLY views of the Record (the `raw`
area) and of the revisions index, used only to PROVE a staged copy is promoted; and (3) in apply mode only, a
`DriveStagingTrash`. That class has no general delete: it accepts a staged copy's parts (source, archive path, fetch
stamp), builds `staging/...` itself, and hard-refuses any path not strictly inside `staging/`, again at the last step
before Drive. In report-only mode no deleter is built at all. The limit is in this code, not in credentials (the one
Drive credential is shared, as for the promotion gate), and it is pinned by tests with a Record path as the plant.

NSE copies are trashed only when the Record holds the same bytes AND the manifest has that file's SHA-256 (the receipt
chain for a Record file starts at its manifest row). News polls (owner choice (b), 27 Oct 2026) are trashed once every
article in the poll is in the Record; the raw poll's extra fields (body, author, categories, wrapper links) are then
gone for good, because the Record keeps an article's fields, not the raw poll. Each rule is one entry in `proofs()`."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable

from fno.ingestion.news.feeds import PrivateFeedLists
from fno.ingestion.news.fetcher import SOURCE as NEWS_TAG
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.planner import ArticlePlanner
from fno.ingestion.news.record.wrapper_index import WRAPPERS_FILE
from fno.ingestion.news.wiring import CONFIG_AREA, POLL_LOG_FOLDER
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.promotion.wiring import NSE_TAG, STAGING_AREA
from fno.ingestion.staging_cleanup.cleanup import StagingCleanup
from fno.ingestion.staging_cleanup.news_proof import NewsPollProof
from fno.ingestion.staging_cleanup.proof import NseCopyProof, PromotedProof
from fno.ingestion.staging_cleanup.trash import DriveStagingTrash
from fno.ingestion.storage.manifest_folder import ManifestFolder, source_of
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.revisions import RevisionArchive
from fno.ingestion.storage.source_lists import RAW_SOURCES
from fno.ingestion.storage.wiring import (
    OWNER_UPLOAD_SETTINGS,
    RAW_AREA,
    build_manifest_folder,
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


class ArchiveFingerprints:
    """Read-only: the manifest SHA-256 of a Record file (None when its dataset has no manifest or no row for it)."""

    def __init__(self, manifests: ManifestFolder):
        self.manifests = manifests

    def sha256_of(self, path: str) -> str | None:
        try:
            source = source_of(path, RAW_SOURCES)
        except ValueError:
            return None
        return self.manifests.fingerprints(source).get(path.rsplit("/", 1)[-1])


def proofs(
    record: AreaStore, manifests: ManifestFolder, archive: RevisionArchive, kinds: Callable[[], dict[str, str]],
    sources: Iterable[str],
) -> dict[str, PromotedProof]:  # fmt: skip
    """A rule per requested source only: the feed list is read (and can fail) only when news is asked for."""
    wanted = set(sources)
    rules: dict[str, PromotedProof] = {}
    if NSE_TAG in wanted:
        rules[NSE_TAG] = NseCopyProof(record, ArchiveFingerprints(manifests), ArchiveRevisionHolds(archive))
    if NEWS_TAG in wanted:
        rules[NEWS_TAG] = NewsPollProof(
            kinds(), ArticlePlanner(record), NewsManifest(POLL_LOG_FOLDER), NewsManifest(POLL_LOG_FOLDER, WRAPPERS_FILE)
        )
    return rules


def build_staging_cleanup(apply: bool, limit: int, sources: Iterable[str], env=os.environ) -> StagingCleanup:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    staging = StagingArea(AreaStore(drive, STAGING_AREA))
    record = AreaStore(drive, RAW_AREA)
    trash = DriveStagingTrash(drive) if apply else None
    kinds = PrivateFeedLists(AreaStore(drive, CONFIG_AREA)).kinds_ever_listed
    rules = proofs(record, build_manifest_folder(), build_revision_archive(env), kinds, sources)
    return StagingCleanup(staging, rules, trash, limit=limit)
