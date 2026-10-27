"""One article as the dashboard and the later steps see it (NP5b; the read contract NP7 builds on): the recorded article
file joined with its resolution file (NP2c) and its read file (NP4b), and judged by the rules of the day: tier and
opinion (NP1), agency origin, promotional, the companies it is about (the tagger), and whether it is material. Pure and
computed on every read: nothing here is stored, so editing a rule or the company list re-judges old articles by design
and never changes a recorded byte. The source URL is spoof-resistant: it comes only from the resolution file or from a
publisher item's own link, never from the feed text, a label or a page."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.materiality.terms import MaterialTerms
from fno.ingestion.news.origins.origin import OriginReader
from fno.ingestion.news.origins.promotional import PromotionalFilter
from fno.ingestion.news.reads.read_file import ReadFile
from fno.ingestion.news.resolve.resolution_file import Resolution
from fno.ingestion.news.sources.model import UNLISTED
from fno.ingestion.news.sources.rules import SourceRules, plain_host
from fno.ingestion.news.tagging.tagger import Tag, Tagger


@dataclass(frozen=True)
class ArticleView:
    key: str
    url: str  # the effective source URL: the resolution's, else the publisher's own link, else ""
    host: str
    tier: str
    listed: bool
    opinion: bool
    wire: str
    promotional: bool
    tag: Tag
    material: bool
    access: str  # the read file's outcome ("" when the page was not read)


class ArticleViewer:
    def __init__(self, rules: SourceRules, tagger: Tagger, terms: MaterialTerms):
        self.rules, self.tagger, self.terms = rules, tagger, terms
        self.origins, self.promotions = OriginReader(rules), PromotionalFilter(rules)

    def view(self, article: Article, resolution: Resolution | None = None, read: ReadFile | None = None) -> ArticleView:
        url = resolution.url if resolution else article.canonical_url
        parts = urlsplit(url) if url else None
        host = plain_host(parts.hostname) if parts else ""  # the domain a feed CLAIMS is never a host (NP0 s.3)
        provider, authors = (read.provider, read.authors) if read else ("", ())
        tag = self.tagger.tag(article.title, article.summary, article.source)
        tier = self.rules.tier_of(host)
        return ArticleView(
            key=article.key,
            url=url,
            host=host,
            tier=tier,
            listed=tier != UNLISTED,
            opinion=self.rules.is_opinion(host, parts.path if parts else None),
            wire=self.origins.read(host, provider, authors, article.title).wire,
            promotional=self.promotions.check(
                host, provider, authors, article.source, article.title, article.summary
            ).promotional,
            tag=tag,
            material=self.terms.is_material(article.title, tag, article.source),
            access=read.access if read else "",
        )
