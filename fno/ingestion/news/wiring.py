"""Composition root of the news fetch (P2a): the only place that picks concrete stores. The fetcher gets an AreaStore on
`staging`, so it cannot reach the Record (`raw`); the feed list is read from the private `config` area of the same Drive
folder. The poll log is the repository's only record of a poll: feed id, path, SHA-256 and size (no URL, no title)."""

from __future__ import annotations

import os

from fno.ingestion.news.feeds import PrivateFeedLists
from fno.ingestion.news.fetcher import NewsFetcher
from fno.ingestion.news.job import NewsFetchJob
from fno.ingestion.news.session import NewsSession
from fno.ingestion.news.snapshot_log import NewsSnapshotLog
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.promotion.wiring import STAGING_AREA
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.wiring import MANIFEST_FOLDER, OWNER_UPLOAD_SETTINGS, build_owner_drive
from fno.shared.models import now_utc

CONFIG_AREA = "config"  # private: the feed lists (invariant 1 of P2)
POLL_LOG_FOLDER = MANIFEST_FOLDER / "news"
NEEDS_DRIVE = "set {settings} to fetch news"


def build_news_fetch(env=os.environ) -> NewsFetchJob:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    log = NewsSnapshotLog(POLL_LOG_FOLDER)
    staging = StagingArea(AreaStore(drive, STAGING_AREA))
    fetcher = NewsFetcher(NewsSession(), staging, log, now_utc)
    return NewsFetchJob(PrivateFeedLists(AreaStore(drive, CONFIG_AREA)), fetcher, log, now_utc)
