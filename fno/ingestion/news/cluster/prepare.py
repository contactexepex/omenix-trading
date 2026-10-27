"""Clustering algorithm version 2's preparation of an article (NP6a): what moves the title bar and what an article's URL
says.

Version 1 prepares with a fixed list of 22 names in code (`entities.py`, kept so old files stay reproducible). Version
2 asks the `Tagger` (NP5a) which of the owner's companies the TITLE names (never the summary: a passing mention in a
summary is only `mentioned` and must not move a bar), passing the article's source so an outlet suffix never tags
(judge 92 F2), and takes the identity URL from the resolution file or the item's own link (`resolve/effective_url.py`,
`url_identity.py`)."""

from __future__ import annotations

from collections.abc import Mapping

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.cluster.matcher import Prepared
from fno.ingestion.news.cluster.title_text import shingles, title_form
from fno.ingestion.news.cluster.url_identity import identity_of
from fno.ingestion.news.cluster.window import story_time
from fno.ingestion.news.resolve.effective_url import effective_url
from fno.ingestion.news.resolve.resolution_file import Resolution
from fno.ingestion.news.tagging.tagger import Tagger

GROUPER_VERSION = "2"


class Preparer:
    version = GROUPER_VERSION

    def __init__(self, tagger: Tagger, resolutions: Mapping[str, Resolution]):
        """`resolutions`: article key -> its resolution file (only the Google News items that have one)."""
        self.tagger, self.resolutions = tagger, resolutions

    def prepare(self, article: Article) -> Prepared:
        symbols = frozenset(self.tagger.tag(article.title, None, article.source).symbols)
        identity = identity_of(effective_url(article, self.resolutions.get(article.key)))
        return Prepared(
            article, shingles(title_form(article.title)), symbols, story_time(article), identity.url, identity.refused
        )
