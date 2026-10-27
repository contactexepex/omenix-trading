"""P2b1: the canonical URL, the time, the key and the article file, as pure functions."""

from __future__ import annotations

import random
import string
from datetime import UTC, datetime

import pytest

from fno.ingestion.news.article.article_file import build_article
from fno.ingestion.news.article.canonical import canonical_url
from fno.ingestion.news.article.keys import PUBLISHER, WRAPPER, item_key
from fno.ingestion.news.article.raw_item import RawItem
from fno.ingestion.news.article.times import ASSUMED_UTC, PUBLISHED, SEEN, parse_time
from tests.ingestion.news.article.samples import SEEN as SEEN_AT

# ---- the canonical URL (D3) ----------------------------------------------------------------------


def test_only_the_allow_list_is_stripped_and_the_rest_is_kept_in_sorted_order():
    url = "HTTPS://Pub.Example:443/a/b?z=1&utm_source=x&UTM_Medium=y&id=123&fbclid=q&gclid=1&igshid=2&mc_cid=3&mc_eid=4#top"
    assert canonical_url(url) == "https://pub.example/a/b?id=123&z=1"


def test_two_urls_that_differ_only_in_tracking_give_one_key_and_in_a_real_parameter_give_two():
    one = canonical_url("https://pub.example/a?id=123&utm_source=a")
    assert one == canonical_url("https://pub.example/a?utm_campaign=b&id=123")
    assert canonical_url("https://pub.example/a?id=123") != canonical_url("https://pub.example/a?id=124")


@pytest.mark.parametrize("url", ["https://p.example/a?b=1&a=2", "http://p.example:8080/x?q=%20z", "https://p.example/"])
def test_canonicalising_twice_changes_nothing(url):
    assert canonical_url(canonical_url(url)) == canonical_url(url)


def test_a_non_default_port_and_a_blank_value_are_kept():
    assert canonical_url("http://p.example:8080/x?flag=") == "http://p.example:8080/x?flag="


# ---- the time ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected", "source"),
    [
        ("Tue, 27 Oct 2026 08:00:00 +0530", datetime(2026, 10, 27, 2, 30, tzinfo=UTC), PUBLISHED),
        ("Tue, 27 Oct 2026 08:00:00 GMT", datetime(2026, 10, 27, 8, 0, tzinfo=UTC), PUBLISHED),
        ("2026-10-27T02:30:00Z", datetime(2026, 10, 27, 2, 30, tzinfo=UTC), PUBLISHED),
        ("2026-10-27T08:00:00+05:30", datetime(2026, 10, 27, 2, 30, tzinfo=UTC), PUBLISHED),
        ("2026-10-27T08:00:00", datetime(2026, 10, 27, 8, 0, tzinfo=UTC), ASSUMED_UTC),  # no zone: UTC, flagged
        ("2031-01-01T00:00:00Z", datetime(2031, 1, 1, tzinfo=UTC), PUBLISHED),  # the future is accepted, never rejected
        # judge 46 E2: four digits after a decimal point, a comma or a T are a fraction or a time, never a year
        ("2026-10-26T10:00:00.1234Z", datetime(2026, 10, 26, 10, 0, 0, 123400, tzinfo=UTC), PUBLISHED),
        ("2026-10-26T10:00:00,1234Z", datetime(2026, 10, 26, 10, 0, 0, 123400, tzinfo=UTC), PUBLISHED),
        ("2026-10-26T1234Z", datetime(2026, 10, 26, 12, 34, tzinfo=UTC), PUBLISHED),
        ("", None, SEEN),
        ("last Tuesday", None, SEEN),
    ],
)
def test_times_are_read_in_utc_with_their_source(text, expected, source):
    assert parse_time(text) == (expected, source)


# ---- the key (D2) --------------------------------------------------------------------------------


def item(**kw):
    return RawItem(**{"title": "T", "link": "https://pub.example/a/1", **kw})


MOMENT = datetime(2026, 10, 27, 2, 30, 0, tzinfo=UTC)


def test_the_key_is_deterministic_and_a_64_character_hex_digest():
    key = item_key(PUBLISHER, item(), MOMENT)
    assert key == item_key(PUBLISHER, item(), MOMENT) and len(key) == 64 and set(key) <= set(string.hexdigits.lower())


def test_a_publisher_key_ignores_tracking_and_title_and_follows_the_real_url():
    base = item_key(PUBLISHER, item(), MOMENT)
    assert base == item_key(PUBLISHER, item(link="https://pub.example/a/1?utm_source=x#frag", title="edited"), MOMENT)
    assert base != item_key(PUBLISHER, item(link="https://pub.example/a/2"), MOMENT)
    assert base != item_key(PUBLISHER, item(link="https://pub.example/a/1?id=2"), MOMENT)


def test_a_publisher_item_without_a_link_is_keyed_by_its_guid_and_kinds_never_share_keys():
    assert item_key(PUBLISHER, item(link="", guid="g1"), MOMENT) != item_key(
        PUBLISHER, item(link="", guid="g2"), MOMENT
    )
    assert item_key(PUBLISHER, item(link="", guid="g1"), MOMENT) != item_key(WRAPPER, item(link="", guid="g1"), MOMENT)


def test_a_wrapper_item_with_a_guid_is_one_article_across_polls_even_if_the_title_changes():
    a = item_key(WRAPPER, item(guid="gn-1", title="First"), MOMENT)
    assert a == item_key(WRAPPER, item(guid="gn-1", title="Edited", summary="new"), None)


def test_wrapper_items_without_a_guid_two_same_title_items_a_minute_apart_get_two_keys_and_identical_copies_one():
    first = item_key(WRAPPER, item(title="Stocks to watch today"), MOMENT)
    later = item_key(WRAPPER, item(title="Stocks to watch today"), MOMENT.replace(minute=31))
    assert first != later
    assert first == item_key(WRAPPER, item(title="  STOCKS  to watch today "), MOMENT)  # normalised: one article


def test_distinct_inputs_never_collide_over_a_large_random_batch():
    rng = random.Random(7)
    seen = {}
    for n in range(3000):
        link = f"https://pub.example/{rng.randrange(10**9)}/{n}?id={rng.randrange(10**6)}"
        key = item_key(PUBLISHER, item(link=link), MOMENT)
        assert seen.setdefault(key, link) == link
    assert len(seen) == 3000


def test_the_separator_stops_two_splits_of_the_same_letters_sharing_a_key():
    a = item_key(WRAPPER, item(title="ab", summary="c"), MOMENT)
    b = item_key(WRAPPER, item(title="a", summary="bc"), MOMENT)
    assert a != b


# ---- the article file (D4) -----------------------------------------------------------------------


def test_the_same_item_gives_the_same_bytes_and_a_later_poll_changes_only_first_seen_at():
    a = build_article(PUBLISHER, item(published="Tue, 27 Oct 2026 08:00:00 +0530", summary="s", source="X"), SEEN_AT)
    again = build_article(
        PUBLISHER, item(published="Tue, 27 Oct 2026 08:00:00 +0530", summary="s", source="X"), SEEN_AT
    )
    later = build_article(PUBLISHER, item(published="Tue, 27 Oct 2026 08:00:00 +0530", summary="s", source="X"),
                         SEEN_AT.replace(hour=9))  # fmt: skip
    assert (
        a.to_bytes() == again.to_bytes()
        and a.fixed_fields() == later.fixed_fields()
        and a.to_bytes() != later.to_bytes()
    )


def test_a_changed_title_or_summary_changes_the_fixed_fields_so_it_is_a_revision():
    a = build_article(PUBLISHER, item(summary="s"), SEEN_AT)
    assert a.fixed_fields() != build_article(PUBLISHER, item(title="Corrected", summary="s"), SEEN_AT).fixed_fields()
    assert a.fixed_fields() != build_article(PUBLISHER, item(summary="s2"), SEEN_AT).fixed_fields()


def test_a_wrapper_article_holds_no_url_and_an_item_without_a_time_is_kept_as_seen():
    wrapper = build_article(WRAPPER, item(link="https://wrapper.example/redirect?x=1", guid="g", published=""), SEEN_AT)
    assert wrapper.canonical_url == "" and wrapper.time_source == SEEN and wrapper.published_at == ""
    assert b"redirect" not in wrapper.to_bytes()


@pytest.mark.parametrize("text", ["00010101T000000+0500", "99991231T235959-0500"])
def test_a_time_with_no_standalone_year_that_overflows_on_conversion_is_no_time_not_an_error(text):
    """judge 46 E1: the year pre-check cannot see these, so the OverflowError clause is what keeps them from raising."""
    assert parse_time(text) == (None, SEEN)


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        (
            "Thu, 01 Jan 2015 10:00:00 +0000",
            True,
        ),  # a real 2015 item keeps its time in both formats: the band is not an age check
        ("2015-01-01T10:00:00Z", True),
        ("Mon, 01 Jan 1990 00:00:00 +0000", True),  # the band edges, RFC 822 and RFC 3339
        ("1990-01-01T00:00:00Z", True),
        ("Sun, 31 Dec 1989 00:00:00 +0000", False),
        ("1989-12-31T23:59:59Z", False),
        ("Fri, 31 Dec 2100 12:00:00 +0000", True),
        ("2100-12-31T23:00:00Z", True),
        ("Sat, 01 Jan 2101 00:00:00 +0000", False),
        ("2101-01-01T00:00:00Z", False),
        ("18500101T000000Z", False),  # a compact RFC 3339 form is judged by its parsed year too
    ],
)
def test_the_year_band_is_not_an_age_check_and_its_edges_are_1990_and_2100(text, kept):
    moment, source = parse_time(text)
    assert (moment is not None, source == PUBLISHED) == (kept, kept)
    assert kept or source == SEEN


def test_a_four_digit_fraction_keeps_its_real_time_on_the_rfc_3339_path():
    """judge 46 E2: `.1234` and `.5000` are fractions of a second, never years; the time keeps its microseconds."""
    assert parse_time("2026-10-26T10:00:00.1234Z") == (datetime(2026, 10, 26, 10, 0, 0, 123400, tzinfo=UTC), PUBLISHED)
    assert parse_time("2026-10-26T10:00:00.5000+05:30") == (
        datetime(2026, 10, 26, 4, 30, 0, 500000, tzinfo=UTC),
        PUBLISHED,
    )
