"""Composition root of the recall report (NP11): read-only stores only. The Record and the private config area are
read; nothing is written, so there is no writer, no data store and no receipt here."""

from __future__ import annotations

import os

from fno.ingestion.news.cluster_record.article_source import ArticleSource
from fno.ingestion.news.cluster_record.grouping import SymbolGrouping
from fno.ingestion.news.companies.private_file import PrivateCompanyFile
from fno.ingestion.news.provenance.index import ProvenanceIndex
from fno.ingestion.news.provenance.recall import RecallRun
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.wiring import CONFIG_AREA, POLL_LOG_FOLDER
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.wiring import OWNER_UPLOAD_SETTINGS, RAW_AREA, build_owner_drive

NEEDS_DRIVE = "set {settings} to measure recall"


def build_recall(env=os.environ) -> RecallRun:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    record = AreaStore(drive, RAW_AREA)
    grouping = SymbolGrouping(PrivateCompanyFile(AreaStore(drive, CONFIG_AREA)), record)
    return RecallRun(ArticleSource(record, NewsManifest(POLL_LOG_FOLDER)), grouping, ProvenanceIndex(record))
