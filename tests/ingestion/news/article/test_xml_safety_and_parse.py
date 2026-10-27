"""P2b1: hostile XML is refused on the raw bytes before any parser sees it, and the three feed formats are read."""

from __future__ import annotations

from xml.etree import ElementTree

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.article.parse_feed import PollRejected, parse_poll
from fno.ingestion.news.article.xml_safety import MAX_POLL_BYTES, refusal
from tests.ingestion.news.article.samples import ATOM, BILLION_LAUGHS, RDF, XXE, rss, rss_item

CLEAN = rss(rss_item())


@pytest.mark.parametrize("hostile", [BILLION_LAUGHS, XXE], ids=["billion-laughs", "external-entity"])
def test_a_billion_laughs_and_an_xxe_are_refused_before_any_parse(hostile, monkeypatch):
    def never(*args, **kwargs):
        raise AssertionError("the parser was reached")

    monkeypatch.setattr(ElementTree, "fromstring", never)
    with pytest.raises(PollRejected) as refused:
        parse_poll(hostile)
    assert str(refused.value) == codes.UNSAFE_XML


@pytest.mark.parametrize(
    "variant",
    [
        b"<!DOCTYPE r>" + CLEAN,
        b"<!doctype r>" + CLEAN,
        b"<!DocType r>" + CLEAN,
        b"   \n\t<?xml version='1.0'?>\n  <!DOCTYPE r [<!entity x 'y'>]><rss/>",
        b"\xef\xbb\xbf<?xml version='1.0'?><!DOCTYPE r><rss/>",  # a UTF-8 BOM
        "<?xml version='1.0'?><!DOCTYPE r><rss/>".encode("utf-16"),  # UTF-16 with a BOM
        "<?xml version='1.0'?><!DOCTYPE r><rss/>".encode("utf-16-le"),  # UTF-16 without one
        "<?xml version='1.0'?><!DOCTYPE r><rss/>".encode("utf-32"),
        b"<rss><!ENTITY x 'y'></rss>",
    ],
)
def test_the_declaration_is_found_whatever_the_case_white_space_bom_or_encoding(variant):
    assert refusal(variant) == codes.UNSAFE_XML


def test_a_clean_feed_is_not_refused_and_an_oversized_poll_is():
    assert MAX_POLL_BYTES == 5 * 1024 * 1024  # the number itself, so raising it is a decision a test notices
    assert refusal(CLEAN) is None
    assert refusal(b"x" * (MAX_POLL_BYTES + 1)) == codes.POLL_TOO_LARGE
    assert refusal(b"x" * MAX_POLL_BYTES) is None


def test_the_three_formats_are_read_into_items():
    (rss_one,) = parse_poll(rss(rss_item(title="T", link="https://pub.example/x", guid="g1", source="Outlet X")))
    assert (rss_one.title, rss_one.link, rss_one.guid, rss_one.source) == (
        "T",
        "https://pub.example/x",
        "g1",
        "Outlet X",
    )
    (atom,) = parse_poll(ATOM)
    assert atom.title == "Atom story" and atom.link == "https://pub.example/atom/1"  # rel=alternate, not rel=self
    assert atom.guid == "tag:pub,1" and atom.published == "2026-10-27T02:30:00Z" and atom.source == "Atom outlet"
    (rdf,) = parse_poll(RDF)
    assert (
        rdf.title == "Rdf story" and rdf.link == "https://pub.example/rdf/1" and rdf.published.startswith("2026-10-27")
    )


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"not xml at all", codes.NOT_A_FEED),
        (b"<html><body>consent</body></html>", codes.NOT_A_FEED),
        (b"<rss><channel><item><title>cut", codes.NOT_A_FEED),  # truncated
        (b"<rss version='2.0'><channel><title>x</title></channel></rss>", codes.NO_ITEMS),
        (b"\xff\xfe\x00bad", codes.NOT_A_FEED),
    ],
)
def test_a_poll_that_is_not_a_usable_feed_is_refused_with_a_fixed_code(data, code):
    with pytest.raises(PollRejected) as refused:
        parse_poll(data)
    assert str(refused.value) == code and refused.value.__cause__ is None
