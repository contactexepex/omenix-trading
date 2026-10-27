"""Composition root of the page-read pass (NP4b): the only place that picks the concrete stores and the fetcher. The
Record is read only; read files go out through the write-once writer alone, with a receipt per Drive file and a row in
`reads.csv`. The four manifests are read from the checkout when the pass is built."""

from __future__ import annotations

import os
import time

from fno.ingestion.news.pages.wiring import build_page_fetcher
from fno.ingestion.news.reads.read_file import key_of_path
from fno.ingestion.news.reads.run import ReadPass
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.wrapper_index import WRAPPERS_FILE
from fno.ingestion.news.resolve.wiring import RESOLVED_MANIFEST
from fno.ingestion.news.sources.loader import load_source_rules
from fno.ingestion.news.wiring import POLL_LOG_FOLDER
from fno.ingestion.news.write_once import WriteOnceWriter
from fno.ingestion.storage.data_store import DataStore, new_run_id
from fno.ingestion.storage.data_wiring import batch_receipt_writer
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.wiring import OWNER_UPLOAD_SETTINGS, RAW_AREA, build_owner_drive
from fno.shared.models import now_utc

READER_WRITER = "news-read"
READS_MANIFEST = "reads.csv"
NEEDS_DRIVE = "set {settings} to read news pages"


def build_read_pass(env=os.environ) -> ReadPass:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    record = AreaStore(drive, RAW_AREA)
    run_id = new_run_id(now_utc())
    store = DataStore(drive, RAW_AREA, batch_receipt_writer(run_id), READER_WRITER, run_id)
    writer = WriteOnceWriter(record, store, NewsManifest(POLL_LOG_FOLDER, READS_MANIFEST), key_of_path)
    rules = load_source_rules()
    return ReadPass(
        record,
        NewsManifest(POLL_LOG_FOLDER),
        NewsManifest(POLL_LOG_FOLDER, WRAPPERS_FILE),
        NewsManifest(POLL_LOG_FOLDER, RESOLVED_MANIFEST),
        build_page_fetcher(),
        rules,
        writer,
        time.monotonic,
    )
