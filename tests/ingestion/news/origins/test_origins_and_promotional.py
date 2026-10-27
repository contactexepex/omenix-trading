"""NP5b: agency origins and promotional content, from facts only, against hand-made public-style rules."""

from __future__ import annotations

import pytest

from fno.ingestion.news.origins.origin import BYLINE, DOMAIN, PROVIDER, TITLE, OriginReader, attributions
from fno.ingestion.news.origins.promotional import PHRASE, PromotionalFilter
from fno.ingestion.news.sources.loader import build_source_rules

RULES = build_source_rules({
    "domains": {
        "wire-a.example": {"tier": "primary"},
        "pub.example": {"tier": "tier1"},
        "vendor.example": {"tier": "tier2"},
    },
    "wires": {
        "AgencyA": {"names": ["AgencyA", "AgencyA Staff"], "attribution": ["AgencyA"], "domains": ["wire-a.example"]},
        "AgencyB": {"names": ["AgencyB", "AB"], "attribution": ["AgencyB"], "domains": ["wire-b.example"]},
    },
    "promotional": {
        "providers": ["Vendor Rank"], "domains": ["vendor.example"],
        "text": ["sponsored (?:content|post)", "Rank #", r"Mid \(Target\)"],
    },
})  # fmt: skip
READER, FILTER = OriginReader(RULES), PromotionalFilter(RULES)


def test_an_article_on_an_agencys_own_domain_is_that_agencys_story():
    assert READER.read("www.wire-a.example", None, (), "Title").wire == "AgencyA"
    assert READER.read("sub.wire-b.example", None, (), "Title").via == DOMAIN


def test_the_json_ld_provider_and_a_byline_name_the_agency_whole_and_in_any_case():
    assert READER.read("pub.example", "agencya staff", (), "T") == READER.read("pub.example", "AgencyA Staff", (), "T")
    assert READER.read("pub.example", "AgencyA Staff", (), "T").via == PROVIDER
    byline = READER.read("pub.example", "Pub Daily", ["Some Writer", "AgencyB"], "T")
    assert (byline.wire, byline.via) == ("AgencyB", BYLINE)
    assert READER.read("pub.example", "Pub Daily", ["AgencyA Weekly"], "T").wire == ""  # whole names only


@pytest.mark.parametrize(
    "title",
    [
        "Rates unchanged (AgencyA)",
        "Rates unchanged [AgencyA]",
        "Rates unchanged - AgencyA",
        "Rates unchanged | AgencyA",
    ],
)
def test_a_title_that_ends_with_an_attribution_to_the_agency_is_its_story(title):
    origin = READER.read("pub.example", None, (), title)
    assert (origin.wire, origin.via) == ("AgencyA", TITLE)


def test_a_title_that_only_mentions_an_agency_is_not_a_copy_of_it():
    for title in (
        "AgencyA reports rates unchanged",
        "Rates (unchanged) after AgencyA poll",
        "Rates unchanged - Pub Daily",
        "Rates (AgencyA) hold, analysts say",
        "AgencyA - rates hold, analysts say",
    ):
        assert READER.read("pub.example", None, (), title).wire == "", title
    assert READER.read("pub.example", None, (), None).wire == "" and READER.read(None, None, (), "").wire == ""


def test_the_attribution_labels_are_bounded_and_found_at_the_end_only():
    assert attributions("x" * 5000 + " (AgencyA)") == []  # past the title cap
    assert attributions("A - B - C") == ["C"] and attributions("") == []


def test_a_listed_promotional_provider_byline_source_or_domain_is_promotional():
    assert FILTER.check("pub.example", "Vendor Rank", (), None, "T", "").via == "provider"
    assert FILTER.check("pub.example", None, ["vendor rank"], None, "T", "").promotional
    assert FILTER.check("pub.example", None, (), "Vendor Rank", "T", "").promotional
    assert FILTER.check("www.vendor.example", None, (), None, "T", "").via == "domain"
    assert not FILTER.check("pub.example", "Pub Daily", ["Writer"], "Pub Daily", "T", "S").promotional


def test_a_marker_phrase_in_the_title_or_the_cleaned_summary_is_promotional():
    assert FILTER.check("pub.example", None, (), None, "Sponsored Content: buy now", "").via == PHRASE
    assert FILTER.check("pub.example", None, (), None, "T", "<p>See our Rank # 1 pick</p>").promotional
    assert FILTER.check(
        "pub.example", None, (), None, "Price Mid (Target) raised", ""
    ).promotional  # escaped parentheses
    assert not FILTER.check("pub.example", None, (), None, "Sponsorship of a content hub", "plain").promotional


def test_a_marker_phrase_beyond_the_text_cap_or_inside_a_link_is_not_seen():
    assert not FILTER.check("pub.example", None, (), None, "x " * 600 + "sponsored content", "").promotional
    assert not FILTER.check(
        "pub.example", None, (), None, "T", '<a href="https://sponsored.example/content">x</a>'
    ).promotional


def test_the_phrases_come_from_the_rules_and_every_one_is_safe():
    from fno.ingestion.news.sources.loader import load_source_rules

    shipped = PromotionalFilter(load_source_rules())
    assert (
        len(shipped.phrases) == 8
        and shipped.check("pub.example", None, (), None, "Zacks Rank # 1 stock", "").promotional
    )
