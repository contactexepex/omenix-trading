"""Composition root of the cluster record (P2d): the only place that picks concrete stores. Articles and the earlier
cluster file are read from the Record (`raw`, read only); the cluster file goes out through the ClusterWriter alone,
with a receipt per Drive file and a row in `clusters.csv`. The articles manifest is read from the checkout to choose
which articles to read.
"""

from __future__ import annotations

import os

from fno.ingestion.news.cluster.prepare import GROUPER_VERSION
from fno.ingestion.news.cluster_record.article_source import ArticleSource
from fno.ingestion.news.cluster_record.grouping import SymbolGrouping
from fno.ingestion.news.cluster_record.run import ClusterRun
from fno.ingestion.news.cluster_record.writer import ClusterWriter
from fno.ingestion.news.companies.private_file import PrivateCompanyFile
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.wiring import CONFIG_AREA, POLL_LOG_FOLDER
from fno.ingestion.storage.data_store import DataStore, new_run_id
from fno.ingestion.storage.data_wiring import batch_receipt_writer
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.wiring import OWNER_UPLOAD_SETTINGS, RAW_AREA, build_owner_drive
from fno.shared.models import now_utc

WRITER = "news-cluster"
ALGORITHM_1 = "1"
CLUSTERS_MANIFEST = "clusters.csv"
NEEDS_DRIVE = "set {settings} to cluster news"


def build_news_cluster(env=os.environ, algorithm: str = ALGORITHM_1) -> ClusterRun:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    record = AreaStore(drive, RAW_AREA)
    run_id = new_run_id(now_utc())
    store = DataStore(drive, RAW_AREA, batch_receipt_writer(run_id), WRITER, run_id)
    writer = ClusterWriter(record, store, NewsManifest(POLL_LOG_FOLDER, CLUSTERS_MANIFEST))
    grouping = (
        SymbolGrouping(PrivateCompanyFile(AreaStore(drive, CONFIG_AREA)), record)
        if algorithm == GROUPER_VERSION
        else None
    )
    return ClusterRun(ArticleSource(record, NewsManifest(POLL_LOG_FOLDER)), writer, record, grouping)
