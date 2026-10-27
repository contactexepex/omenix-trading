"""NP9: a Google News item is stored with the clean headline: the " - Outlet" it appends is dropped at ingestion, and
only when it is the outlet the feed itself names (cleaning verifies nothing; the verified publisher is the resolved
host)."""

from __future__ import annotations

from fno.ingestion.news.article.article_file import build_article
from fno.ingestion.news.article.keys import PUBLISHER, WRAPPER, item_key
from fno.ingestion.news.article.raw_item import RawItem
from fno.ingestion.news.text_rules import fold, without_outlet
from tests.ingestion.news.article.samples import SEEN as SEEN_AT

LINK = "https://news.example/rss/articles/abc"


def wrapper(title: str, source: str = "Daily Ledger", **kw) -> RawItem:
    return RawItem(**{"title": title, "link": LINK, "guid": "gn-1", "source": source, **kw})


def test_a_wrapper_titles_outlet_suffix_is_dropped_from_the_stored_title():
    article = build_article(WRAPPER, wrapper("Acme Ltd posts record profit - Daily Ledger"), SEEN_AT)
    assert article.title == "Acme Ltd posts record profit"


def test_a_suffix_that_is_not_the_feeds_claimed_outlet_is_kept():
    article = build_article(
        WRAPPER, wrapper("Acme Ltd posts record profit - Other Paper", source="Daily Paper"), SEEN_AT
    )
    assert article.title == "Acme Ltd posts record profit - Other Paper"


def test_a_publisher_item_keeps_its_title_whatever_the_ending():
    article = build_article(PUBLISHER, wrapper("Acme Ltd posts record profit - Daily Ledger"), SEEN_AT)
    assert article.title == "Acme Ltd posts record profit - Daily Ledger"


def test_the_key_comes_from_the_raw_item_so_cleaning_never_makes_a_revision():
    raw = wrapper("Acme Ltd posts record profit - Daily Ledger", guid="")
    clean = wrapper("Acme Ltd posts record profit", guid="")
    assert item_key(WRAPPER, raw, None) != item_key(WRAPPER, clean, None)  # with no guid the key reads the title
    assert build_article(WRAPPER, raw, SEEN_AT).key == item_key(WRAPPER, raw, None)


def test_the_same_item_gives_the_same_bytes_on_a_re_poll():
    item = wrapper("Acme Ltd posts record profit - Daily Ledger")
    assert build_article(WRAPPER, item, SEEN_AT).to_bytes() == build_article(WRAPPER, item, SEEN_AT).to_bytes()


def test_a_title_that_is_only_the_outlet_or_ends_in_its_name_as_a_word_is_kept():
    assert without_outlet("Daily Ledger", "Daily Ledger") == "Daily Ledger"
    assert without_outlet("Acme joins the Daily Ledger", "Daily Ledger") == "Acme joins the Daily Ledger"
    assert without_outlet("Acme news", None) == "Acme news"


def test_a_curly_quote_in_the_outlet_name_still_matches_and_the_headline_keeps_its_own_quotes():
    assert without_outlet("Acme’s year - Reader’s Digest", "Reader's Digest") == "Acme’s year"


def test_a_stored_title_is_never_emptied_by_the_cut():
    assert without_outlet("- Daily Ledger", "Daily Ledger") == ""  # the helper itself; build_article guards it
    article = build_article(WRAPPER, wrapper("- Daily Ledger"), SEEN_AT)
    assert article.title == "- Daily Ledger"


def test_a_no_break_space_folds_to_a_plain_space_so_it_cannot_hide_the_outlet():
    assert fold("a b") == "a b" and fold("Acme’s") == "Acme's"
    assert without_outlet("Rates rise - Daily Ledger", "Daily Ledger") == "Rates rise"
    article = build_article(WRAPPER, wrapper("Rates rise - Daily Ledger"), SEEN_AT)
    assert article.title == "Rates rise"


def test_a_no_break_space_beside_the_separator_is_cut_with_it_and_the_headline_keeps_its_own_text():
    """Judge 116: the cut ran on the original text, so only a plain space beside the separator was removed."""
    assert without_outlet("Rates rise - Daily Ledger", "Daily Ledger") == "Rates rise"
    assert without_outlet("Rates rise - Daily Ledger", "Daily Ledger") == "Rates rise"
    assert without_outlet("Acme’s rates rise  | Daily Ledger", "Daily Ledger") == "Acme’s rates rise"
    article = build_article(WRAPPER, wrapper("Rates rise - Daily Ledger"), SEEN_AT)
    assert article.title == "Rates rise"
