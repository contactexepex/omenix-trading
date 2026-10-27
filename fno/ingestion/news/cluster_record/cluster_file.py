"""The cluster file (P2d): one run's clusters as deterministic JSON, at a path that holds the algorithm version and the
window end, so a changed algorithm is a new path and a closed window is one name. Hash ids and counts only: no title,
URL, query, feed or outlet. The same clustering always gives the same bytes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fno.ingestion.news.cluster.cluster import Cluster, Clustering
from fno.ingestion.news.cluster.prepare import GROUPER_VERSION
from fno.ingestion.news.cluster.window import WINDOW

FORMAT = 1  # version 1 files
FORMAT_2 = 2  # version 2 files: the same, plus how the run was fed and what the URL rule did (NP6a)
FORMATS = (FORMAT, FORMAT_2)
CLUSTERS_FOLDER = "news/clusters"
STAMP = "%Y%m%dT%H%M%SZ"
INPUT_RULE = "first seen at or before the window end; max(published, first seen) within the window before it"


def stamp_of(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime(STAMP)


def window_end_of(name: str) -> datetime | None:
    """The window end a file name holds, or None for a name that is not one of ours."""
    try:
        return datetime.strptime(name.removesuffix(".json"), STAMP).replace(tzinfo=UTC)
    except ValueError:
        return None


def cluster_folder(version: str) -> str:
    return f"{CLUSTERS_FOLDER}/{version}"


def cluster_path(version: str, as_of: datetime) -> str:
    return f"{cluster_folder(version)}/{stamp_of(as_of)}.json"


def path_id(path: str) -> str:
    """The manifest id of a cluster file: the SHA-256 of its path (64 hex, like an article id)."""
    return hashlib.sha256(path.encode("ascii")).hexdigest()


def cluster_file_bytes(clustering: Clustering) -> bytes:
    document = {
        "format": FORMAT_2 if clustering.algorithm_version == GROUPER_VERSION else FORMAT,
        "algorithm_version": clustering.algorithm_version,
        "window_end": stamp_of(clustering.as_of),
        "window_hours": int(WINDOW / timedelta(hours=1)),
        "input_rule": INPUT_RULE,
        "clustered": clustering.clustered,
        "outside_window": clustering.outside_window,
        "repeated_keys": clustering.repeated_keys,
        "clusters": [
            {
                "cluster_id": c.cluster_id,
                "anchor_key": c.anchor_key,
                "member_keys": list(c.member_keys),
                "previous_cluster_ids": list(c.previous_cluster_ids),
            }
            for c in clustering.clusters
        ],
    }
    if document["format"] == FORMAT_2:
        document |= {
            "companies_version": clustering.companies_version,
            "companies_sha256": clustering.companies_sha256,
            "resolutions_used": clustering.resolutions_used,
            "url_joins": clustering.url_joins,
            "url_joins_refused": clustering.url_joins_refused,
            "url_joins_unlike_title": clustering.url_joins_unlike_title,
        }
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


@dataclass(frozen=True)
class ClusterFile:
    version: str
    window_end: datetime
    window_hours: int
    clusters: tuple[Cluster, ...]
    companies_version: int = 0  # format 2 files; 0 for format 1 and for a run that had no list
    companies_sha256: str = ""


def parse_cluster_file(data: bytes) -> ClusterFile:
    """Raises ValueError for anything that is not a cluster file of ours (the caller counts it, never trusts it)."""
    try:
        document = json.loads(data)
        end = window_end_of(document["window_end"])
        clusters = tuple(
            Cluster(c["cluster_id"], c["anchor_key"], tuple(c["member_keys"]), tuple(c["previous_cluster_ids"]))
            for c in document["clusters"]
        )
        if document["format"] not in FORMATS or end is None:
            raise ValueError("unknown format")
        return ClusterFile(
            document["algorithm_version"], end, int(document["window_hours"]), clusters,
            int(document.get("companies_version", 0)), str(document.get("companies_sha256", "")),
        )  # fmt: skip
    except (KeyError, TypeError, AttributeError, UnicodeDecodeError) as broken:
        raise ValueError("not a cluster file") from broken
