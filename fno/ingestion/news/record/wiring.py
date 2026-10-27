"""Composition root of the news promotion (P2b2): the only place that picks concrete stores. The gate reads the
`staging` area and the private `config` feed list (for each feed's kind) and writes the Record (`raw`, with a receipt
per Drive file and a row in the news manifest) through the ArticleWriter only."""

from __future__ import annotations

import os

from fno.ingestion.news.feeds import PrivateFeedLists
from fno.ingestion.news.provenance.index import ProvenanceIndex
from fno.ingestion.news.provenance.model import PROVENANCE_FILE, provenance_id
from fno.ingestion.news.provenance.writer import ProvenanceWriter
from fno.ingestion.news.record.gate import NewsGate
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.wrapper_index import WrapperIndex
from fno.ingestion.news.record.writer import ArticleWriter
from fno.ingestion.news.wiring import CONFIG_AREA, POLL_LOG_FOLDER
from fno.ingestion.news.write_once import WriteOnceWriter
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.promotion.wiring import STAGING_AREA
from fno.ingestion.storage.data_store import DataStore, new_run_id
from fno.ingestion.storage.data_wiring import batch_receipt_writer
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.wiring import OWNER_UPLOAD_SETTINGS, RAW_AREA, build_owner_drive
from fno.shared.models import now_utc

WRITER = "news-promote"
NEEDS_DRIVE = "set {settings} to promote news"


def build_news_promotion(env=os.environ) -> NewsGate:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    lists = PrivateFeedLists(AreaStore(drive, CONFIG_AREA))
    kinds = lists.kinds_ever_listed()
    run_id = new_run_id(now_utc())
    store = DataStore(drive, RAW_AREA, batch_receipt_writer(run_id), WRITER, run_id)
    writer = ArticleWriter(
        AreaStore(drive, RAW_AREA), store, NewsManifest(POLL_LOG_FOLDER), WrapperIndex(POLL_LOG_FOLDER)
    )
    record = AreaStore(drive, RAW_AREA)
    provenance = ProvenanceWriter(
        ProvenanceIndex(record),
        WriteOnceWriter(record, store, NewsManifest(POLL_LOG_FOLDER, PROVENANCE_FILE), provenance_id),
        lists.latest().salt,
    )
    return NewsGate(StagingArea(AreaStore(drive, STAGING_AREA)), writer, kinds, provenance, lists.scopes_ever_listed())
