"""Composition root of the cluster record (P2d): the only place that picks concrete stores. Articles and the earlier
cluster file are read from the Record (`raw`, read only); the cluster file goes out through the ClusterWriter alone,
with a receipt per Drive file and a row in `clusters.csv`. The articles manifest is read from the checkout to choose
which articles to read.
"""

from __future__ import annotations

import os

from fno.ingestion.news.cluster_record.article_source import ArticleSource
from fno.ingestion.news.cluster_record.run import ClusterRun
from fno.ingestion.news.cluster_record.writer import ClusterWriter
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.wiring import POLL_LOG_FOLDER
from fno.ingestion.storage.data_store import DataStore, new_run_id
from fno.ingestion.storage.data_wiring import receipt_folder
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.wiring import OWNER_UPLOAD_SETTINGS, RAW_AREA, build_owner_drive
from fno.shared.models import now_utc

WRITER = "news-cluster"
CLUSTERS_MANIFEST = "clusters.csv"
NEEDS_DRIVE = "set {settings} to cluster news"


def build_news_cluster(env=os.environ) -> ClusterRun:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    record = AreaStore(drive, RAW_AREA)
    store = DataStore(drive, RAW_AREA, receipt_folder(), WRITER, new_run_id(now_utc()))
    writer = ClusterWriter(record, store, NewsManifest(POLL_LOG_FOLDER, CLUSTERS_MANIFEST))
    return ClusterRun(ArticleSource(record, NewsManifest(POLL_LOG_FOLDER)), writer, record)
