"""Articles into stories (P2c): a pure function. It takes article values and returns clusters of keys; reads no store,
no clock and no network, writes nothing, and holds no title, URL or feed in anything it returns (P2d writes the file).

Every article inside the window is in exactly one cluster (invariant 4: clustering never hides an article); articles
outside the window, and repeats of a key, are counted, not dropped silently. Same inputs give the same output in any
input order.

**Defaults, not findings** (see `similarity.py`): do not trust anything derived from clusters until the threshold and
the window are re-tuned on real data.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.cluster.assign import assign
from fno.ingestion.news.cluster.cluster_id import cluster_id, replaced_ids
from fno.ingestion.news.cluster.matcher import Matcher, Prepared
from fno.ingestion.news.cluster.similarity import Jaccard, Similarity
from fno.ingestion.news.cluster.window import in_window

ALGORITHM_VERSION = (
    "1"  # bump with any change to the threshold, window, stages or entity list: a new version is a new path
)


@dataclass(frozen=True)
class Cluster:
    cluster_id: str
    anchor_key: str
    member_keys: tuple[str, ...]  # in assignment order, the anchor first
    previous_cluster_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Clustering:
    as_of: datetime
    algorithm_version: str
    clusters: tuple[Cluster, ...]
    outside_window: int  # distinct articles not looked at this run (stay in the Record)
    repeated_keys: int  # inputs whose key was already given

    @property
    def clustered(self) -> int:
        return sum(len(c.member_keys) for c in self.clusters)


def cluster_articles(articles: Iterable[Article], as_of: datetime, previous: Sequence[Cluster] = (),
                     similarity: Similarity | None = None) -> Clustering:  # fmt: skip
    """`previous`: the run before's clusters, to name replaced ids; `similarity`: the measure (Jaccard by default)."""
    given = sorted(
        articles, key=lambda a: (a.first_seen_at, a.key, a.to_bytes())
    )  # a full tie-break: input order never decides
    distinct: dict[str, Article] = {}
    for article in given:
        distinct.setdefault(article.key, article)  # a repeated key is the same article: its earliest sighting is kept
    repeated = len(given) - len(distinct)
    looked_at = [Prepared.of(a) for a in distinct.values() if in_window(a, as_of)]
    earlier = [(c.cluster_id, frozenset(c.member_keys)) for c in previous]
    clusters = []
    for members in assign(looked_at, Matcher(similarity or Jaccard())):
        keys = tuple(m.article.key for m in members)
        new_id = cluster_id(keys[0])
        clusters.append(Cluster(new_id, keys[0], keys, replaced_ids(new_id, keys, earlier)))
    return Clustering(as_of, ALGORITHM_VERSION, tuple(clusters), len(distinct) - len(looked_at), repeated)
