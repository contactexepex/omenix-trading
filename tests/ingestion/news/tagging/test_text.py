"""NP5a: cleaning, capping and word-splitting of the text a tagger sees."""

from __future__ import annotations

import time

from fno.ingestion.news.tagging.text import MAX_RAW, MAX_TEXT, capped, plain_text, word_tuple, words


def test_a_summary_becomes_plain_text_without_tags_entities_links_or_domains():
    html = (
        '<a href="https://news.svc.example/x">Zzalpha &amp; sons rise</a>&nbsp;&nbsp;'
        "<font>Outlet Daily</font> www.pub.example/a"
    )
    assert plain_text(html, "Outlet Daily") == "Zzalpha & sons rise"


def test_a_link_or_a_source_name_never_becomes_text():
    assert plain_text('<a href="https://zzalpha.example/news">read</a>') == "read"
    assert plain_text("Zzbeta rallies - Zzbeta Times", "Zzbeta Times") == "Zzbeta rallies"
    assert plain_text(None) == "" and plain_text("") == ""


def test_typographic_quotes_and_no_break_spaces_are_folded():
    assert plain_text("Zzbeta’s ‘plan’ works") == "Zzbeta's 'plan' works"
    assert capped("Zzbeta’s plan") == "Zzbeta's plan" and capped(None) == ""


def test_a_text_is_cut_after_cleaning_so_the_outlet_suffix_does_not_use_up_the_cap():
    summary = "w" * 990 + " tail " + "x" * 50 + " Outlet Daily"
    cleaned = plain_text(summary, "Outlet Daily")
    assert len(cleaned) == MAX_TEXT and not cleaned.endswith("Outlet Daily")


def test_the_raw_summary_is_cut_before_the_cleaners_run_so_a_huge_one_is_fast():
    start = time.monotonic()
    plain_text("a." * (MAX_RAW * 20))
    plain_text("<" * (MAX_RAW * 20))
    assert time.monotonic() - start < 2


def test_words_keep_ampersands_and_apostrophes_whole_and_give_their_positions():
    assert [w for w, _, _ in words("L&T's Zzalpha, rises")] == ["l&t's", "zzalpha", "rises"]
    assert words("ab cd")[1][1:] == (3, 5) and word_tuple("Zz & Lt  Works") == ("zz", "&", "lt", "works")


def test_the_tag_pattern_never_reads_past_the_next_opening_bracket():
    """What keeps a run of `<` linear: an unclosed tag ends at the next `<`, so only the closed one is removed."""
    from fno.ingestion.news.tagging.text import _TAGS

    assert _TAGS.sub("", "<a <b>") == "<a " and _TAGS.sub("", "x<a>y") == "xy"
