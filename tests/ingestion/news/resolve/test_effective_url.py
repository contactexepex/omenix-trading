"""NP5b, NP6a: the source URL of an article comes only from the resolution file (Google News item) or its own link."""

from __future__ import annotations

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.resolve.effective_url import effective_url
from fno.ingestion.news.resolve.resolution_file import Resolution


def article(**changes) -> Article:
    base = dict(
        key="k" * 64, kind="publisher", source="Pub Daily", title="Zzalpha merger talks", summary="", canonical_url="",
        published_at="", time_source="none", first_seen_at="2026-10-27T03:00:00+00:00",
    )  # fmt: skip
    return Article(**{**base, **changes})


def resolution(url: str) -> Resolution:
    return Resolution("k" * 64, url, "pub.example", "pub.example", True)


def test_a_google_news_article_takes_its_url_only_from_the_resolution_file():
    wrapper = article(kind="wrapper", source_domain="pub.example", wrapper_link="https://wrap.svc.example/rss/a?oc=5")
    assert effective_url(wrapper, None) == ""
    assert effective_url(wrapper, resolution("https://pub.example/news/story")) == "https://pub.example/news/story"


def test_a_publisher_article_takes_its_own_link():
    assert effective_url(article(canonical_url="https://www.pub.example/news/a"), None) == (
        "https://www.pub.example/news/a"
    )


def test_the_feed_text_a_label_or_a_page_can_never_set_the_url():
    assert effective_url(article(summary="see https://evil.example/x", source="evil.example"), None) == ""
