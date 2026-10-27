"""The cluster file writer (P2d): the write-once writer (`news/write_once.py`) with the cluster file's manifest id. A
closed window clusters to stable bytes, so a conflict means the inputs, the algorithm version or the determinism
changed for that window: investigate."""

from __future__ import annotations

from fno.ingestion.news.cluster_record.cluster_file import path_id
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.write_once import WriteOnceWriter, Written
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import RawFileStore

__all__ = ["ClusterWriter", "Written"]


class ClusterWriter(WriteOnceWriter):
    def __init__(self, reader: RawFileStore, store: DataStore, manifest: NewsManifest):
        super().__init__(reader, store, manifest, path_id)
