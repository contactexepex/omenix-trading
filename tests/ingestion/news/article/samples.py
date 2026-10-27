"""Hand-written synthetic feeds for the article-gate tests (no real feed bytes): every title and URL is made up."""

from __future__ import annotations

from datetime import UTC, datetime

SEEN = datetime(2026, 10, 27, 3, 0, 0, tzinfo=UTC)


def rss(*items: str, extra: str = "") -> bytes:
    head = "<?xml version='1.0'?><rss version='2.0'><channel><title>Outlet</title>"
    return f"{head}{extra}{''.join(items)}</channel></rss>".encode()


def rss_item(
    title="Story one",
    link="https://pub.example/a/1",
    guid="",
    pub="Tue, 27 Oct 2026 08:00:00 +0530",
    desc="d",
    source="",
    source_url="",
) -> str:
    parts = [f"<title>{title}</title>" if title is not None else ""]
    parts += [f"<link>{link}</link>" if link else "", f"<guid>{guid}</guid>" if guid else ""]
    parts += [f"<pubDate>{pub}</pubDate>" if pub else "", f"<description>{desc}</description>" if desc else ""]
    attribute = f' url="{source_url}"' if source_url else ""
    parts += [f"<source{attribute}>{source}</source>" if source else ""]
    return f"<item>{''.join(parts)}</item>"


ATOM = (
    b"<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'><title>Atom outlet</title>"
    b"<entry><title>Atom story</title><link rel='self' href='https://pub.example/self'/>"
    b"<link rel='alternate' href='https://pub.example/atom/1'/><id>tag:pub,1</id>"
    b"<published>2026-10-27T02:30:00Z</published><summary>sum</summary></entry></feed>"
)
RDF = (
    b"<?xml version='1.0'?><rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
    b"xmlns='http://purl.org/rss/1.0/' xmlns:dc='http://purl.org/dc/elements/1.1/'>"
    b"<item rdf:about='https://pub.example/rdf/1'><title>Rdf story</title><link>https://pub.example/rdf/1</link>"
    b"<dc:date>2026-10-27T03:00:00+05:30</dc:date></item></rdf:RDF>"
)
BILLION_LAUGHS = (
    b"<?xml version='1.0'?><!DOCTYPE lolz [<!ENTITY lol 'lol'><!ENTITY lol2 '&lol;&lol;&lol;&lol;'>"
    b"<!ENTITY lol3 '&lol2;&lol2;&lol2;&lol2;'>]><rss><channel><item><title>&lol3;</title></item></channel></rss>"
)
XXE = (
    b"<?xml version='1.0'?><!DOCTYPE r [<!ENTITY x SYSTEM 'file:///etc/passwd'>]>"
    b"<rss><channel><item><title>&x;</title><link>https://p.example/1</link></item></channel></rss>"
)
