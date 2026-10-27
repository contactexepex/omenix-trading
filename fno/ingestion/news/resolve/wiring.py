"""Composition root of the link resolver (NP2b): the only place that picks the concrete adapter. Swapping the library
for our own small adapter is one new class behind `LinkResolver` and one line here."""

from __future__ import annotations

import os
from collections.abc import Iterable

from fno.ingestion.news.feeds import FeedEntry, PrivateFeedLists
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.wrapper_index import WRAPPERS_FILE
from fno.ingestion.news.resolve.decoder_adapter import GoogleNewsDecoderResolver
from fno.ingestion.news.resolve.guard import guard_from_feeds
from fno.ingestion.news.resolve.model import LinkResolver
from fno.ingestion.news.resolve.resolution_file import key_of_path
from fno.ingestion.news.resolve.run import ResolvePass
from fno.ingestion.news.wiring import CONFIG_AREA, POLL_LOG_FOLDER
from fno.ingestion.news.write_once import WriteOnceWriter
from fno.ingestion.storage.data_store import DataStore, new_run_id
from fno.ingestion.storage.data_wiring import batch_receipt_writer
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.wiring import OWNER_UPLOAD_SETTINGS, RAW_AREA, build_owner_drive
from fno.shared.models import now_utc


def build_link_resolver(feeds: Iterable[FeedEntry]) -> LinkResolver:
    """A resolver allowed to call only the domains of the wrapper feeds in `feeds` (the private feed list)."""
    return GoogleNewsDecoderResolver(guard_from_feeds(feeds))


RESOLVER_WRITER = "news-resolve"
RESOLVED_MANIFEST = "resolved.csv"
NEEDS_DRIVE = "set {settings} to resolve news links"


def build_resolve_pass(env=os.environ) -> ResolvePass:
    """The Record is read only; resolution files go out through the write-once writer alone. ONE resolver for the whole
    run, so its stop on a refusal and its pacing are never reset between calls."""
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    record = AreaStore(drive, RAW_AREA)
    feeds = PrivateFeedLists(AreaStore(drive, CONFIG_AREA)).latest().feeds
    run_id = new_run_id(now_utc())
    store = DataStore(drive, RAW_AREA, batch_receipt_writer(run_id), RESOLVER_WRITER, run_id)
    writer = WriteOnceWriter(record, store, NewsManifest(POLL_LOG_FOLDER, RESOLVED_MANIFEST), key_of_path)
    return ResolvePass(record, NewsManifest(POLL_LOG_FOLDER, WRAPPERS_FILE), build_link_resolver(feeds), writer)
