"""NP5a: which companies a headline is about (invented companies only)."""

from __future__ import annotations

import time

import pytest

from fno.ingestion.news.companies.model import Company, CompanyList
from fno.ingestion.news.tagging.dictionary import NameDictionary
from fno.ingestion.news.tagging.tagger import HIGH, LOW, Tagger
from fno.ingestion.news.tagging.text import MAX_TEXT
from tests.ingestion.news.tagging.helpers import COMPANIES, TAGGER, tag


def test_a_company_named_alone_in_the_title_is_primary_with_high_confidence():
    result = tag("Zzbeta Bank posts record profit")
    assert (result.primary, result.mentioned, result.confidence) == (("ZZBE",), (), HIGH)


def test_names_and_aliases_match_whole_words_in_any_case_and_never_inside_a_longer_word():
    assert tag("ZZALPHA surges").primary == ("ZZAL",) and tag("zzalpha holdings surges").primary == ("ZZAL",)
    for headline in ("Zzalphabet soup", "Unzzalpha news", "Zzalpha_x rises", "Zzalphas rise"):
        assert tag(headline).symbols == ()


def test_the_longest_name_wins_at_a_position_and_names_do_not_overlap():
    assert tag("Zzalpha Bank cuts rates").primary == ("ZZAB",)  # not Zzalpha Holdings' alias "Zzalpha"
    assert tag("Zzalpha Holdings cuts rates").primary == ("ZZAL",)


def test_a_name_with_punctuation_matches_as_written_in_the_text():
    assert tag("ZZ&LT wins order").primary == ("ZZLT",) and tag("Zz & Lt Works wins order").primary == ("ZZLT",)


def test_a_symbol_in_brackets_is_a_company_only_in_capitals_and_in_brackets():
    assert tag("Shares of the lender (ZZDE) rise").primary == ("ZZDE",)
    assert tag("Shares rise (NSE: ZZDE)").primary == ("ZZDE",) and tag("Shares rise (ZZDE:NSE)").primary == ("ZZDE",)
    for headline in ("Shares of ZZDE rise", "Shares rise (zzde)", "Shares rise [ZZDE]", "Shares rise (ZZDEX)"):
        assert tag(headline).symbols == (), headline


def test_a_phrase_the_owner_excluded_does_not_tag_its_company():
    assert tag("Zzgamma Foods Lanka expands").symbols == ()
    assert tag("Zzgamma Foods and Zzgamma Foods Lanka expand").primary == ("ZZGA",)  # one plain mention remains
    assert tag("Zzomega Hospitality opens hotel").symbols == () and tag("Zzomega opens plant").primary == ("ZZOM",)


def test_the_summary_is_used_only_when_the_title_names_nobody_and_then_only_as_mentioned():
    result = tag("Markets close higher", "<p>Gains led by Zzdelta and Zzbeta Bank</p>")
    assert (result.primary, result.mentioned, result.confidence) == ((), ("ZZBE", "ZZDE"), LOW)
    assert tag("Zzdelta gains", "Zzbeta Bank also rose").primary == (
        "ZZDE",
    )  # the title decides; the summary is ignored
    assert tag("Zzdelta gains", "Zzbeta Bank also rose").mentioned == ()


def test_a_search_link_or_a_source_name_in_the_summary_tags_nobody():
    assert tag("Markets close higher", '<a href="https://zzdelta.example/x">read</a>', "Zzdelta Daily").symbols == ()
    assert tag("Markets close higher", "Markets rise - Zzdelta Times", "Zzdelta Times").symbols == ()


def test_a_comparison_title_makes_its_companies_mentioned_with_low_confidence():
    for title in ("Zzalpha vs Zzbeta: which to buy", "Zzalpha versus Zzbeta", "Zzalpha v/s Zzbeta"):
        result = tag(title)
        assert (result.primary, result.mentioned, result.confidence) == ((), ("ZZAL", "ZZBE"), LOW), title


def test_a_list_of_companies_is_mentioned_but_a_comma_after_a_lone_company_is_not_a_list():
    listed = tag("Zzalpha, Zzbeta and Zzdelta rise")
    assert listed.primary == () and listed.mentioned == ("ZZAL", "ZZBE", "ZZDE") and listed.confidence == LOW
    assert tag("Zzalpha / Zzbeta rally").mentioned == ("ZZAL", "ZZBE")
    lone = tag("Zzalpha, the largest holding company, rises")
    assert (lone.primary, lone.mentioned, lone.confidence) == (("ZZAL",), (), HIGH)  # mine: a list needs two companies


def test_several_companies_in_a_sentence_that_is_not_a_list_are_all_primary_with_low_confidence():
    result = tag("Zzalpha acquires Zzdelta for a premium")
    assert (result.primary, result.mentioned, result.confidence) == (("ZZAL", "ZZDE"), (), LOW)


def test_nothing_tagged_is_empty():
    result = tag("Markets close higher", "Nothing to see")
    assert (result.primary, result.mentioned, result.confidence, result.symbols) == ((), (), "", ())
    assert tag(None).symbols == () and tag("").symbols == ()


def test_only_the_first_thousand_characters_are_looked_at():
    assert tag("x " * (MAX_TEXT // 2) + "Zzdelta rises").symbols == ()
    assert tag("Zzdelta rises " + "x " * 2000).primary == ("ZZDE",)
    assert tag("Markets", "y " * (MAX_TEXT // 2) + "Zzdelta rises").symbols == ()


def test_a_long_summary_with_a_heavy_exclusion_finishes_inside_a_bound():
    """The hard time bound: bounded text times a bounded pattern."""
    group = "(?:" + "|".join(["zzfiller"] * 5) + ")"
    heavy = Company("ZZHV", "Zzheavy", exclusions=(group + group + r"a?a?b\w*",))
    tagger = Tagger(NameDictionary(CompanyList(1, (*COMPANIES, heavy))))
    start = time.monotonic()
    result = tagger.tag("Markets", "zzfiller zzfiller " * 3000 + "Zzheavy rises")
    assert time.monotonic() - start < 2 and result.symbols == ()  # beyond the cap, nothing is seen


def test_a_dictionary_is_built_from_the_injected_list_and_never_names_a_company_itself():
    assert NameDictionary(CompanyList(7, ())).longest == 0 and NameDictionary(CompanyList(7, ())).version == 7
    assert Tagger(NameDictionary(CompanyList(1, ()))).tag("Zzalpha rises").symbols == ()
    assert TAGGER.dictionary.symbols == {c.symbol for c in COMPANIES}


@pytest.mark.parametrize("bad", ["(unclosed", ".*.*x", "a*"])
def test_an_exclusion_that_is_no_longer_safe_is_dropped_not_fatal(bad):
    company = Company("ZZXX", "Zzxx", exclusions=(bad,))
    assert Tagger(NameDictionary(CompanyList(1, (company,)))).tag("Zzxx rises").primary == ("ZZXX",)


def test_hits_never_looks_past_the_cap_even_when_called_directly():
    assert TAGGER.hits("x " * (MAX_TEXT // 2) + "Zzdelta rises") == []
    assert [h.symbol for h in TAGGER.hits("Zzdelta rises")] == ["ZZDE"]


def test_a_possessive_is_the_company_and_a_plural_word_is_not():
    assert tag("Zzalpha's profit jumps 20%").primary == ("ZZAL",) and tag("Zzalpha Bank’s profit").primary == ("ZZAB",)
    assert tag("Zzalpha's, Zzbeta's and Zzdelta's shares rise").confidence == LOW
    assert tag("Zzalphas rise").symbols == ()
    assert tag("Zzbeta's Q2 beats").confidence == HIGH
    two = tag("Zzalpha, Zzbeta's results")  # judge 93 B1: a list of two, not one high-confidence company
    assert (two.primary, two.mentioned, two.confidence) == ((), ("ZZAL", "ZZBE"), LOW)


def test_the_outlet_name_after_a_separator_never_tags_but_the_same_word_in_the_headline_does():
    assert tag("Markets close higher - Zzalpha", None, "Zzalpha").symbols == ()
    assert tag("Markets close higher | Zzalpha", None, "Zzalpha").symbols == ()
    assert tag("Markets rally as Zzalpha", None, "Zzalpha").primary == ("ZZAL",)
    assert tag("Zzbeta Bank profit - Zzalpha", None, "Zzalpha").primary == ("ZZBE",)


def test_an_exchange_label_in_a_colon_bracket_is_not_a_symbol():
    for headline in ("Shares rise (BSE: 500325)", "Shares rise (NSE: 500325)", "Shares rise (ZZDE: BSE)"):
        assert "BSE" not in tag(headline).symbols, headline
    assert tag("Shares rise (BSE: ZZDE)").primary == ("ZZDE",)
    assert tag("Shares of the exchange (BSE) rise").primary == ("BSE",)  # a lone bracketed symbol is still one
