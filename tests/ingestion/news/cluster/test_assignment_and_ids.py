"""P2c: the anchor rule (no chaining), the cluster id and the ids a cluster replaces."""

from __future__ import annotations

import hashlib
from datetime import timedelta

from fno.ingestion.news.cluster.cluster import cluster_articles
from tests.ingestion.news.cluster.helpers import AS_OF, art, at, keys_of, words


def test_similarity_is_not_chained_a_like_b_and_b_like_c_do_not_put_a_and_c_together():
    a, b, c = art("a", words(1, 12), at(5)), art("b", words(3, 14), at(4)), art("c", words(5, 16), at(3))
    assert keys_of(cluster_articles([c, b, a], AS_OF)) == [("a", "b"), ("c",)]


def test_an_article_like_two_anchors_joins_the_earlier_and_the_two_clusters_are_not_merged():
    x, y = art("x", words(1, 10), at(6)), art("y", words(7, 16), at(5))
    z = art("z", words(1, 16), at(4))
    assert keys_of(cluster_articles([z, y, x], AS_OF)) == [("x", "z"), ("y",)]


def test_the_cluster_id_is_the_hash_of_the_earliest_articles_key_and_ties_go_to_the_smaller_key():
    same_moment = at(3)
    result = cluster_articles([art("b", words(1, 8), same_moment), art("a", words(1, 8), same_moment)], AS_OF)
    [cluster] = result.clusters
    assert cluster.anchor_key == "a" and cluster.member_keys == ("a", "b")
    assert cluster.cluster_id == hashlib.sha256(b"a").hexdigest()


def test_the_anchor_is_the_earliest_by_publication_time_not_by_arrival():
    late_seen_early_story = art("old", words(1, 8), at(10), seen=at(1))
    quick = art("new", words(1, 8), at(2))
    [cluster] = cluster_articles([quick, late_seen_early_story], AS_OF).clusters
    assert cluster.anchor_key == "old"


def test_an_earlier_article_arriving_changes_the_id_and_the_new_cluster_names_the_old_one():
    first = cluster_articles([art("b", words(1, 8), at(4))], AS_OF)
    again = cluster_articles([art("b", words(1, 8), at(4)), art("a", words(1, 8), at(6))], AS_OF, first.clusters)
    [old], [new] = first.clusters, again.clusters
    assert new.cluster_id != old.cluster_id and new.previous_cluster_ids == (old.cluster_id,)
    assert first.clusters[0].previous_cluster_ids == ()


def test_an_anchor_that_leaves_the_window_re_anchors_and_names_the_old_id():
    early = cluster_articles([art("a", words(1, 8), at(40)), art("b", words(1, 8), at(30))], AS_OF)
    later = AS_OF + timedelta(hours=12)  # a (40 h before AS_OF) is now over 48 h old; b (30 h) is not
    after = cluster_articles([art("a", words(1, 8), at(40)), art("b", words(1, 8), at(30))], later, early.clusters)
    [new] = after.clusters
    assert new.anchor_key == "b" and new.previous_cluster_ids == (early.clusters[0].cluster_id,)
    assert after.outside_window == 1


def test_an_unchanged_cluster_names_nothing():
    arts = [art("a", words(1, 8), at(6)), art("b", words(1, 8), at(4))]
    first = cluster_articles(arts, AS_OF)
    assert cluster_articles(arts, AS_OF, first.clusters).clusters == first.clusters
