"""NP3c: the counts of a clustering comparison (invented articles; counts only)."""

from __future__ import annotations

from fno.ingestion.news.cluster.cluster import Cluster, Clustering
from fno.ingestion.news.compare import metrics
from tests.ingestion.news.cluster.helpers import AS_OF, art
from tests.ingestion.news.tagging.helpers import TAGGER


def clustering(*groups: tuple[str, ...]) -> Clustering:
    clusters = tuple(Cluster(f"c{i}", g[0], g) for i, g in enumerate(groups))
    return Clustering(AS_OF, "1", clusters, 0, 0)


def test_the_shape_counts_clusters_singletons_the_largest_and_the_size_buckets():
    shape = metrics.shape_of(clustering(("a",), ("b", "c"), ("d", "e", "f"), tuple("ghijkl"), tuple("mnopqrstuvwx")))
    assert (shape.clusters, shape.singletons, shape.largest) == (5, 1, 12)
    assert shape.sizes == (1, 1, 1, 1)  # two, three to five, six to ten, eleven or more
    assert metrics.shape_of(clustering()) == metrics.Shape(0, 0, 0, (0, 0, 0, 0))


def test_a_cluster_that_merges_or_splits_the_others_is_counted_once_each_way():
    first = clustering(("a", "b"), ("c",), ("d", "e"))
    second = clustering(("a", "b", "c"), ("d",), ("e",))  # c joins a, b; d, e are split
    cross = metrics.crossing(first, second)
    assert (cross.merged_by_second, cross.split_by_second) == (1, 1)
    same = metrics.crossing(first, first)
    assert (same.merged_by_second, same.split_by_second) == (0, 0)


def test_only_the_articles_both_hold_are_compared():
    cross = metrics.crossing(clustering(("a", "b"), ("c",)), clustering(("a", "b", "x")))
    assert (cross.merged_by_second, cross.split_by_second) == (0, 0)


def test_coverage_counts_tagged_high_confidence_and_how_many_companies_reach_each_threshold():
    articles = [art(str(n), "Zzalpha rises") for n in range(6)] + [art("b", "Zzbeta and Zzdelta"), art("n", "Nothing")]
    cover = metrics.coverage(articles, TAGGER)
    assert (cover.articles, cover.tagged, cover.tagged_high) == (8, 7, 6)
    assert cover.companies_with_at_least == (3, 1, 0)  # alpha 6, beta 1, delta 1


def test_the_metrics_hold_no_key_title_or_symbol():
    shape, cross = metrics.shape_of(clustering(("a",))), metrics.crossing(clustering(("a",)), clustering(("a",)))
    cover = metrics.coverage([art("k", "Zzalpha rises")], TAGGER)
    shown = repr((shape, cross, cover))
    assert "Zzalpha" not in shown and "ZZAL" not in shown and "'k'" not in shown
