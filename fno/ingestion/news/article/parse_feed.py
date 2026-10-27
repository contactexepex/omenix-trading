"""Reading a staged poll into items (P2b): RSS 2.0, Atom and RDF/RSS 1.0, with the standard library only, and only
after the raw-bytes refusal in `xml_safety` (no DOCTYPE or ENTITY ever reaches the parser). A poll that cannot be
used raises `PollRejected` carrying one fixed code, never the text that was wrong."""

from __future__ import annotations

from xml.etree import ElementTree

from fno.ingestion.news import codes
from fno.ingestion.news.article.raw_item import RawItem
from fno.ingestion.news.article.xml_safety import refusal

ATOM = "{http://www.w3.org/2005/Atom}"
RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RSS1 = "{http://purl.org/rss/1.0/}"
DC = "{http://purl.org/dc/elements/1.1/}"


class PollRejected(Exception):
    """A staged poll cannot be used; `str(error)` is the fixed code."""


def _text(element, *names: str) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
    return ""


def _atom_link(entry) -> str:
    links = entry.findall(f"{ATOM}link")
    chosen = next((x for x in links if x.get("rel", "alternate") == "alternate"), links[0] if links else None)
    return (chosen.get("href") or "").strip() if chosen is not None else ""


def _rss_item(item) -> RawItem:
    return RawItem(
        title=_text(item, "title", f"{RSS1}title"),
        link=_text(item, "link", f"{RSS1}link") or (item.get(f"{RDF}about") or "").strip(),
        guid=_text(item, "guid"),
        published=_text(item, "pubDate", f"{DC}date"),
        summary=_text(item, "description", f"{RSS1}description"),
        source=_text(item, "source"),
    )


def _atom_entry(entry, feed_title: str) -> RawItem:
    return RawItem(
        title=_text(entry, f"{ATOM}title"),
        link=_atom_link(entry),
        guid=_text(entry, f"{ATOM}id"),
        published=_text(entry, f"{ATOM}published", f"{ATOM}updated"),
        summary=_text(entry, f"{ATOM}summary", f"{ATOM}content"),
        source=feed_title,
    )


def parse_poll(data: bytes) -> tuple[RawItem, ...]:
    """Every item of the poll; PollRejected(code) for a poll that is refused, not a feed, or empty."""
    code = refusal(data)
    if code:
        raise PollRejected(code)
    try:
        root = ElementTree.fromstring(data)
    except (ElementTree.ParseError, ValueError):
        raise PollRejected(codes.NOT_A_FEED) from None
    if root.tag == "rss" or root.tag == f"{RDF}RDF":
        items = tuple(_rss_item(i) for i in root.iter() if i.tag in ("item", f"{RSS1}item"))
    elif root.tag == f"{ATOM}feed":
        title = _text(root, f"{ATOM}title")
        items = tuple(_atom_entry(e, title) for e in root.findall(f"{ATOM}entry"))
    else:
        raise PollRejected(codes.NOT_A_FEED)
    if not items:
        raise PollRejected(codes.NO_ITEMS)
    return items
