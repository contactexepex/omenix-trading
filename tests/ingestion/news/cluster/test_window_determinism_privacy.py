"""P2c: who is looked at (R2), nothing hidden (invariant 4), same in any order, no title in any output, no I/O."""

from __future__ import annotations

import ast
import dataclasses
import json
import random
from datetime import timedelta
from pathlib import Path

from fno.ingestion.news.cluster.cluster import ALGORITHM_VERSION, cluster_articles
from fno.ingestion.news.cluster.window import WINDOW, effective_time
from tests.ingestion.news.cluster.helpers import AS_OF, art, at, keys_of, words
from tests.ingestion.news.fakes import MARK_HEADLINE, MARK_HOST, MARK_PATH, MARK_QUERY

PACKAGE = Path(__file__).resolve().parents[4] / "fno" / "ingestion" / "news" / "cluster"


def test_a_late_arrival_published_days_ago_but_first_seen_now_is_clustered():
    late = art("late", words(1, 8), published=at(100), seen=at(1))
    assert effective_time(late) == AS_OF - timedelta(hours=1)
    assert keys_of(cluster_articles([late], AS_OF)) == [("late",)]


def test_an_old_article_first_seen_long_ago_is_outside_the_window_and_counted_not_lost():
    old = art("old", words(1, 8), published=at(100), seen=at(99))
    result = cluster_articles([old, art("now", words(30, 38), at(2))], AS_OF)
    assert keys_of(result) == [("now",)] and result.outside_window == 1


def test_an_article_not_yet_seen_at_the_runs_end_is_left_for_a_later_run():
    future = art("future", words(1, 8), published=at(3), seen=(AS_OF + timedelta(hours=1)).isoformat())
    assert cluster_articles([future], AS_OF).outside_window == 1
    assert keys_of(cluster_articles([future], AS_OF + timedelta(hours=2))) == [("future",)]


def test_the_window_is_inclusive_at_its_edge_and_not_beyond():
    edge = art("edge", words(1, 8), published=(AS_OF - WINDOW).isoformat(), seen=(AS_OF - WINDOW).isoformat())
    past = art("past", words(20, 28), published=(AS_OF - WINDOW - timedelta(seconds=1)).isoformat(),
               seen=(AS_OF - WINDOW - timedelta(seconds=1)).isoformat())  # fmt: skip
    result = cluster_articles([edge, past], AS_OF)
    assert keys_of(result) == [("edge",)] and result.outside_window == 1


def test_an_article_with_no_publication_time_counts_as_published_when_first_seen():
    unknown = dataclasses.replace(art("u", words(1, 8), "", seen=at(2)), time_source="seen")
    assert keys_of(cluster_articles([unknown], AS_OF)) == [("u",)]


def test_every_article_in_the_window_is_in_exactly_one_cluster():
    arts = [art(f"k{n:02d}", words(n * 3, n * 3 + 7), at(40 - n)) for n in range(25)]
    arts += [art("dup-of-k00", words(0, 7), at(40)), art("lone", "completely unrelated headline text here", at(1))]
    result = cluster_articles(arts, AS_OF)
    in_clusters = [key for cluster in result.clusters for key in cluster.member_keys]
    assert sorted(in_clusters) == sorted({a.key for a in arts} - set(outside_keys(arts)))
    assert len(in_clusters) == len(set(in_clusters)) == result.clustered
    assert result.clustered + result.outside_window == len({a.key for a in arts})


def outside_keys(arts):
    return [a.key for a in arts if not (AS_OF - WINDOW <= effective_time(a) <= AS_OF)]


def test_a_repeated_key_is_one_article_and_counted():
    result = cluster_articles([art("k", words(1, 8), at(5)), art("k", words(1, 8), at(5), seen=at(4))], AS_OF)
    assert keys_of(result) == [("k",)] and result.repeated_keys == 1


def test_any_input_order_gives_the_same_clustering():
    arts = [art(f"k{n:02d}", words(n % 7 * 2 + 1, n % 7 * 2 + 9), at(30 - n)) for n in range(40)]
    expected = cluster_articles(arts, AS_OF)
    shuffler = random.Random(20261027)
    for _ in range(40):
        shuffled = arts[:]
        shuffler.shuffle(shuffled)
        assert cluster_articles(shuffled, AS_OF) == expected


def test_the_same_inputs_give_the_same_bytes():
    arts = [art("a", words(1, 8), at(6)), art("b", words(1, 8), at(4))]
    first, second = (
        json.dumps(dataclasses.asdict(cluster_articles(arts, AS_OF)), default=str, sort_keys=True) for _ in "12"
    )
    assert first == second and cluster_articles(arts, AS_OF).algorithm_version == ALGORITHM_VERSION


def test_nothing_of_the_story_is_in_what_clustering_returns():
    url = f"https://{MARK_HOST}/{MARK_PATH}?q={MARK_QUERY}"
    one = dataclasses.replace(
        art("a", f"{MARK_HEADLINE} nifty rally today", at(5)), canonical_url=url, summary=MARK_HEADLINE
    )
    two = dataclasses.replace(art("b", f"{MARK_HEADLINE} nifty rally today", at(4)), canonical_url=url)
    result = cluster_articles([one, two], AS_OF)
    shown = repr(result) + json.dumps(dataclasses.asdict(result), default=str)
    for marker in (MARK_HEADLINE, MARK_HOST, MARK_PATH, MARK_QUERY, "Outlet", "nifty"):
        assert marker not in shown
    assert keys_of(result) == [("a", "b")]


def test_the_package_does_no_io_and_reads_no_clock():
    imported, called = set(), set()
    for file in PACKAGE.glob("*.py"):
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called.add(node.func.id)
    assert not imported & {"requests", "urllib", "socket", "subprocess", "os", "pathlib", "logging", "random", "time"}
    assert not called & {"open", "now", "utcnow", "today", "read_text", "write_text", "print"}


def test_a_repeated_key_keeps_its_earliest_sighting_as_the_record_does():
    early = art("k", words(1, 8), at(60), seen=at(60))  # first seen long ago: outside the window
    again = art("k", words(1, 8), at(60), seen=at(1))  # the same article seen again: must not bring it back
    result = cluster_articles([again, early], AS_OF)
    assert result.clusters == () and result.outside_window == 1 and result.repeated_keys == 1
