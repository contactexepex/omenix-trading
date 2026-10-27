"""P2c: when two articles are the same story (stages 1 and 2, the entity as a bar-mover only) and the title form."""

from __future__ import annotations

from fno.ingestion.news.cluster.cluster import cluster_articles
from fno.ingestion.news.cluster.entities import bar_for, entities_in
from fno.ingestion.news.cluster.matcher import Matcher, Prepared
from fno.ingestion.news.cluster.similarity import THRESHOLD, Jaccard, Similarity
from fno.ingestion.news.cluster.title_text import shingles, title_form
from tests.ingestion.news.cluster.helpers import AS_OF, art, at, keys_of, words

SAME = Matcher(Jaccard())


def test_the_same_key_is_the_same_story_whatever_the_titles_and_the_distance_in_time():
    a, b = art("k1", words(1, 8), at(60)), art("k1", words(30, 40), at(2))
    assert SAME.same_story(Prepared.of(a), Prepared.of(b))


def test_a_wrapper_copy_and_its_publisher_copy_of_one_story_are_one_cluster():
    publisher = art("p1", "Nifty ends higher as IT stocks rally", at(3))
    wrapper = art("g1", "Nifty ends higher as IT stocks rally - Economic Times", at(2.9), kind="wrapper")
    assert keys_of(cluster_articles([wrapper, publisher], AS_OF)) == [("p1", "g1")]


def test_the_title_form_drops_case_punctuation_and_a_trailing_outlet_name():
    assert (
        title_form("Nifty Ends Higher, as IT Stocks Rally! - The Economic Times")
        == "nifty ends higher as it stocks rally"
    )
    assert title_form("Sensex | Live Updates | Moneycontrol") == "sensex live updates"  # only the last segment goes
    assert title_form("Budget - Live") == "budget live"  # too short to trim: "Live" is not an outlet name
    assert title_form("RBI holds rates - what it means for the loan market today and next week") == (
        "rbi holds rates what it means for the loan market today and next week"
    )  # a long tail is part of the headline


def test_a_one_word_or_empty_title_has_shingles_and_nothing_crashes():
    assert shingles(title_form("Nifty")) == frozenset({"nifty"}) and shingles(title_form("")) == frozenset()


def test_two_different_nifty_stories_on_one_day_stay_two_clusters():
    one = art("n1", "Nifty ends higher as IT stocks rally", at(5))
    other = art("n2", "Nifty options: traders eye the 25000 call writing ahead of expiry", at(4))
    assert entities_in(title_form(one.title)) & entities_in(title_form(other.title)) == {"nifty"}
    assert keys_of(cluster_articles([one, other], AS_OF)) == [("n1",), ("n2",)]


def test_a_shared_entity_lowers_the_bar_but_never_to_zero():
    nifty = frozenset({"nifty"})
    assert 0 < bar_for(nifty, nifty) < THRESHOLD < bar_for(nifty, frozenset({"sensex"}))
    assert bar_for(frozenset(), frozenset()) == THRESHOLD == bar_for(nifty, frozenset())


def test_a_pair_just_under_the_base_bar_merges_only_with_a_shared_entity():
    shared = (art("a", "nifty " + words(1, 6)), art("b", "nifty " + words(1, 4) + " x00 x01"))
    plain = (art("a", "foo " + words(1, 6)), art("b", "foo " + words(1, 4) + " x00 x01"))
    assert 0.45 <= Jaccard().score(*(Prepared.of(x).shingles for x in shared)) < THRESHOLD
    assert len(cluster_articles(shared, AS_OF).clusters) == 1
    assert len(cluster_articles(plain, AS_OF).clusters) == 2


def test_a_pair_just_over_the_base_bar_is_kept_apart_by_two_different_entities():
    different = (art("a", "nifty " + words(1, 8)), art("b", "sensex " + words(1, 7) + " x00"))
    plain = (art("a", "foo " + words(1, 8)), art("b", "bar " + words(1, 7) + " x00"))
    assert THRESHOLD <= Jaccard().score(*(Prepared.of(x).shingles for x in plain)) < THRESHOLD + 0.1
    assert len(cluster_articles(different, AS_OF).clusters) == 2
    assert len(cluster_articles(plain, AS_OF).clusters) == 1


def test_an_entity_alone_merges_nothing():
    one, other = art("a", "nifty " + words(1, 6)), art("b", "nifty " + words(20, 25))
    assert len(cluster_articles([one, other], AS_OF).clusters) == 2


def test_stories_published_further_apart_than_the_match_window_are_not_the_same_story():
    early, late = art("a", words(1, 8), at(45)), art("b", words(1, 8), at(2))
    assert len(cluster_articles([early, late], AS_OF).clusters) == 2
    assert len(cluster_articles([art("a", words(1, 8), at(30)), late], AS_OF).clusters) == 1


def test_the_similarity_measure_is_swappable_behind_its_interface():
    class Always(Similarity):
        def score(self, a, b):
            return 1.0

    unlike = [art("a", words(1, 8), at(5)), art("b", words(40, 48), at(4))]
    assert len(cluster_articles(unlike, AS_OF).clusters) == 2
    assert len(cluster_articles(unlike, AS_OF, similarity=Always()).clusters) == 1
