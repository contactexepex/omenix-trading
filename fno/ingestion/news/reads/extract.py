"""Facts out of a page (NP4b; NP0 section 2e). Page text is untrusted: it is parsed, measured and discarded, never
executed, never followed, never stored. Two strategies, JSON-LD first and OpenGraph/meta as the fallback, both with
the already hash-locked `selectolax` (no new package: NP4 plan decision 1). What comes out is facts and a hash, not
text: the article body is measured (its length, its SHA-256) and dropped; the few strings kept (names, a time) are
cleaned and capped. `isAccessibleForFree: false` marks a paywalled page."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from selectolax.parser import HTMLParser

from fno.ingestion.news.article.times import parse_time

ARTICLE_TYPES = frozenset({"NewsArticle", "Article", "ReportageNewsArticle", "AnalysisNewsArticle", "BlogPosting",
                           "LiveBlogPosting", "OpinionNewsArticle", "BackgroundNewsArticle"})  # fmt: skip
MAX_JSON_BYTES, MAX_NODES, MAX_DEPTH = 1_000_000, 2_000, 6
MAX_AUTHORS, MAX_NAME = 5, 80
JSON_LD, META = "jsonld", "meta"
CONTROL = re.compile(r"[\x00-\x1f\x7f]+")


@dataclass(frozen=True)
class PageFacts:
    extractor: str
    body_chars: int = 0
    body_sha256: str = ""
    published_at: str = ""
    modified_at: str = ""
    authors: tuple[str, ...] = ()
    provider: str = ""
    paywalled: bool = False


def clean(value: object, limit: int = MAX_NAME) -> str:
    """A short single-line string, or "" for anything else."""
    if not isinstance(value, str):
        return ""
    return CONTROL.sub(" ", value).strip()[:limit].strip()


def utc_time(value: object) -> str:
    moment, _ = parse_time(value) if isinstance(value, str) else (None, "")
    return moment.isoformat(timespec="seconds") if moment else ""


def names(value: object) -> tuple[str, ...]:
    """Author names from a string, a {name} object or a list of either."""
    items = value if isinstance(value, list) else [value]
    found = [clean(item.get("name") if isinstance(item, dict) else item) for item in items[: MAX_AUTHORS * 2]]
    return tuple(dict.fromkeys(n for n in found if n))[:MAX_AUTHORS]


def is_article(node: dict) -> bool:
    kind = node.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    return any(isinstance(k, str) and k in ARTICLE_TYPES for k in kinds)


def article_nodes(document: object) -> list[dict]:
    """The article objects in a JSON-LD document (also inside `@graph` and lists), bounded in depth and count."""
    found, seen, stack = [], 0, [(document, 0)]
    while stack and seen < MAX_NODES:
        node, depth = stack.pop()
        seen += 1
        if isinstance(node, list) and depth < MAX_DEPTH:
            stack.extend((item, depth + 1) for item in node)
        elif isinstance(node, dict):
            if is_article(node):
                found.append(node)
            if depth < MAX_DEPTH and "@graph" in node:
                stack.append((node["@graph"], depth + 1))
    return found


def free_to_read(node: dict) -> bool:
    return str(node.get("isAccessibleForFree", True)).strip().lower() not in ("false", "0")


def from_json_ld(tree: HTMLParser) -> PageFacts | None:
    for script in tree.css('script[type="application/ld+json"]'):
        text = script.text() or ""
        if len(text) > MAX_JSON_BYTES:
            continue
        try:
            nodes = article_nodes(json.loads(text))
        except (ValueError, RecursionError):  # not JSON, or nested past what the parser accepts: this block is skipped
            continue
        if nodes:
            return facts_of(nodes[0])
    return None


def facts_of(node: dict) -> PageFacts:
    body = node.get("articleBody")
    flat = " ".join(body.split()) if isinstance(body, str) else ""
    publisher = node.get("publisher")
    return PageFacts(
        JSON_LD, len(flat), hashlib.sha256(flat.encode()).hexdigest() if flat else "",
        utc_time(node.get("datePublished")), utc_time(node.get("dateModified")), names(node.get("author")),
        clean(publisher.get("name") if isinstance(publisher, dict) else publisher), not free_to_read(node),
    )  # fmt: skip


def meta_content(tree: HTMLParser, selector: str) -> str:
    node = tree.css_first(selector)
    return node.attributes.get("content") or "" if node else ""


def from_meta(tree: HTMLParser) -> PageFacts | None:
    published = utc_time(meta_content(tree, 'meta[property="article:published_time"]'))
    modified = utc_time(meta_content(tree, 'meta[property="article:modified_time"]'))
    authors = names(meta_content(tree, 'meta[name="author"]'))
    provider = clean(meta_content(tree, 'meta[property="og:site_name"]'))
    if not (published or modified or authors or provider):
        return None
    return PageFacts(META, 0, "", published, modified, authors, provider)


def extract(html: bytes) -> PageFacts | None:
    """The facts of one page, or None when it has none of them (an error page, a front page)."""
    tree = HTMLParser(html.decode("utf-8", errors="replace"))
    return from_json_ld(tree) or from_meta(tree)
