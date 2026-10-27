"""NP6a: when a URL can say two articles are one story (invented hosts only)."""

from __future__ import annotations

import pytest

from fno.ingestion.news.cluster.url_identity import Identity, identity_of


def test_a_link_to_one_page_of_one_story_is_an_identity():
    for url in (
        "https://pub.example/news/story-one",
        "https://pub.example/2026/10/27/story",
        "https://pub.example/story-one",  # one segment with a hyphen: a slug
        "https://pub.example/a12345",  # one segment with a digit: an id
        "https://pub.example/?p=77",  # a query identifies the page
    ):
        assert identity_of(url) == Identity(url), url


@pytest.mark.parametrize(
    "url",
    [
        "https://pub.example",
        "https://pub.example/",
        "https://pub.example/markets",  # a section: one plain word
        "https://pub.example/?utm_source=feed",  # only tracking
        "https://pub.example//",
    ],
)
def test_a_home_a_section_or_a_tracking_only_link_is_refused_and_counted_not_joined(url):
    assert identity_of(url) == Identity("", True)


def test_no_link_at_all_is_not_a_refusal():
    assert identity_of("") == Identity("", False)


def test_tracking_parameters_and_the_fragment_are_dropped_and_nothing_else_is_changed():
    plain = identity_of("https://pub.example/news/a?id=7").url
    assert (
        identity_of("https://pub.example/news/a?utm_medium=x&id=7&fbclid=z#top").url
        == plain
        == ("https://pub.example/news/a?id=7")
    )
    assert identity_of("https://pub.example/news/a?id=8").url != plain  # another query is another page
    assert identity_of("https://pub.example/news/a/").url != identity_of("https://pub.example/news/a").url
