"""NP6a: algorithm version 2: company symbols move the bar; an identity URL joins; nothing chains by score."""

from __future__ import annotations

from dataclasses import replace

from fno.ingestion.news.cluster.cluster import cluster_articles
from fno.ingestion.news.cluster.matcher import Prepared
from fno.ingestion.news.cluster.prepare import GROUPER_VERSION, Preparer
from fno.ingestion.news.cluster.similarity import THRESHOLD, Jaccard
from fno.ingestion.news.resolve.resolution_file import Resolution
from tests.ingestion.news.cluster.helpers import AS_OF, art, at, keys_of, words
from tests.ingestion.news.tagging.helpers import TAGGER

PREPARER = Preparer(TAGGER, {})
URL = "https://pub.example/news/story-one"


def group(articles, resolutions=None):
    preparer = Preparer(TAGGER, resolutions or {})
    return cluster_articles(articles, AS_OF, preparer=preparer)


def with_url(article, url):
    return replace(article, canonical_url=url)


def resolved(key, url):
    return Resolution(key, url, "pub.example", "pub.example", True)


def test_a_common_company_lowers_the_bar_and_two_different_companies_raise_it():
    shared = (art("a", "Zzalpha " + words(1, 6)), art("b", "Zzalpha " + words(1, 4) + " x00 x01"))
    assert 0.45 <= Jaccard().score(*(PREPARER.prepare(x).shingles for x in shared)) < THRESHOLD
    assert len(group(shared).clusters) == 1
    plain = (art("a", "foo " + words(1, 6)), art("b", "foo " + words(1, 4) + " x00 x01"))
    assert len(group(plain).clusters) == 2
    different = (art("a", "Zzalpha " + words(1, 8)), art("b", "Zzbeta " + words(1, 7) + " x00"))
    assert len(group(different).clusters) == 2
    assert len(group([art("a", "foo " + words(1, 8)), art("b", "bar " + words(1, 7) + " x00")]).clusters) == 1


def test_the_company_list_not_a_fixed_list_decides_which_names_move_the_bar():
    one = replace(art("a", "nifty " + words(1, 6)))
    two = art("b", "nifty " + words(1, 4) + " x00 x01")
    assert len(cluster_articles([one, two], AS_OF).clusters) == 1  # version 1's own list knows "nifty"
    assert len(group([one, two]).clusters) == 2  # the invented list does not


def test_a_company_in_the_summary_never_moves_the_bar():
    a = replace(art("a", "foo " + words(1, 6)), summary="Zzalpha and Zzalpha")
    b = replace(art("b", "foo " + words(1, 4) + " x00 x01"), summary="Zzalpha again")
    assert PREPARER.prepare(a).entities == frozenset()
    assert len(group([a, b]).clusters) == 2


def test_the_outlet_suffix_of_a_title_never_moves_the_bar():
    a = replace(art("a", "foo " + words(1, 6) + " - Zzalpha"), source="Zzalpha")
    assert PREPARER.prepare(a).entities == frozenset()


def test_two_articles_with_the_same_identity_url_are_one_story_whatever_their_titles():
    result = group([with_url(art("a", words(1, 8)), URL), with_url(art("b", words(20, 28)), URL)])
    assert keys_of(result) == [("a", "b")] and result.url_joins == 1 and result.url_joins_unlike_title == 1
    assert result.algorithm_version == GROUPER_VERSION


def test_a_url_join_that_the_titles_agree_with_is_not_counted_as_unlike():
    result = group([with_url(art("a", words(1, 8)), URL), with_url(art("b", words(1, 8)), URL)])
    assert result.url_joins == 1 and result.url_joins_unlike_title == 0


def test_a_google_news_item_joins_its_publisher_copy_through_its_resolution_file_only():
    wrapper = art("w", words(20, 28), kind="wrapper")
    publisher = with_url(art("p", words(1, 8)), URL)
    assert len(group([wrapper, publisher]).clusters) == 2  # unresolved: the wrapper has no URL at all
    joined = group([wrapper, publisher], {"w": resolved("w", URL)})
    assert keys_of(joined) == [("p", "w")] and joined.url_joins == 1


def test_a_url_that_identifies_no_story_never_joins_and_is_counted():
    home = "https://pub.example/"
    result = group([with_url(art("a", words(1, 8)), home), with_url(art("b", words(20, 28)), home)])
    assert len(result.clusters) == 2 and result.url_joins == 0 and result.url_joins_refused == 2


def test_a_url_join_goes_to_any_member_of_a_cluster_not_only_its_anchor():
    anchor = art("a", "foo " + words(1, 8), at(6))
    by_title = art("b", "foo " + words(1, 8), at(5))  # joins a by its title
    far = with_url(art("c", words(40, 50), at(4)), URL)  # unlike a, but shares b's URL
    b = with_url(by_title, URL)
    result = group([anchor, b, far])
    assert keys_of(result) == [("a", "b", "c")] and result.url_joins == 1


def test_a_title_match_still_compares_with_the_anchor_only_so_a_chain_of_scores_does_not_form():
    a = art("a", words(1, 8), at(6))
    b = art("b", words(3, 10), at(5))  # alike a
    c = art("c", words(5, 12), at(4))  # alike b, not alike a
    assert keys_of(group([a, b, c])) == [("a", "b"), ("c",)]


def test_one_url_belongs_to_the_cluster_that_took_it_first():
    first = with_url(art("a", "foo " + words(1, 8), at(6)), URL)
    other = art("x", words(60, 70), at(5))  # a different story
    again = with_url(art("c", words(80, 90), at(4)), URL)
    third = with_url(art("d", words(80, 90), at(3)), URL)
    result = group([first, other, again, third])
    assert keys_of(result) == [("a", "c", "d"), ("x",)]


def test_the_match_window_still_applies_to_a_url_join():
    old = with_url(art("a", words(1, 8), at(40)), URL)
    new = with_url(art("b", words(1, 8), at(1)), URL)
    assert len(group([old, new]).clusters) == 2


def test_version_one_never_joins_by_url_and_reports_none():
    result = cluster_articles([with_url(art("a", words(1, 8)), URL), with_url(art("b", words(20, 28)), URL)], AS_OF)
    assert len(result.clusters) == 2 and (result.url_joins, result.url_joins_refused) == (0, 0)
    assert Prepared.of(art("a", "x")).url == ""


def test_a_url_stays_with_the_cluster_that_took_it_first_even_when_that_one_is_too_old_to_join():
    first = with_url(art("a", words(1, 8), at(47)), URL)
    second = with_url(art("b", words(20, 28), at(10)), URL)  # 37 h after a: outside the match window, a new cluster
    third = with_url(art("c", words(40, 48), at(1)), URL)  # 9 h after b, but the URL belongs to a's cluster
    assert keys_of(group([first, second, third])) == [("a",), ("b",), ("c",)]
