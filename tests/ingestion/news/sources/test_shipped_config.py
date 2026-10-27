"""NP1: the file the repository ships (config/news_sources.yaml) loads, and says what the plan says it says."""

from __future__ import annotations

from collections import Counter

import pytest

from fno.ingestion.news.sources.loader import load_source_rules


@pytest.fixture(scope="module")
def rules():
    return load_source_rules()


def test_the_shipped_file_loads_with_the_counts_ported_from_agentic(rules):
    assert len(rules.outlets) == 112
    assert Counter(o.tier for o in rules.outlets.values()) == {"primary": 12, "tier1": 23, "tier2": 77}
    assert sum(1 for o in rules.outlets.values() if not o.fetch) == 11
    assert [w.name for w in rules.wires] == ["Reuters", "Bloomberg", "AP", "PTI", "IANS", "ANI", "AFP", "Dow Jones"]


def test_the_exchange_is_primary_and_fetchable_and_the_outlets_that_refuse_bots_are_not(rules):
    assert rules.tier_of("www.nseindia.com") == "primary" and rules.may_fetch("nseindia.com")
    assert rules.tier_of("bseindia.com") == "primary" and not rules.may_fetch("api.bseindia.com")
    for host in ("reuters.com", "apnews.com", "cnbc.com", "marketwatch.com", "ndtvprofit.com"):
        assert not rules.may_fetch(host), host
    assert rules.may_fetch("livemint.com") and rules.tier_of("moneycontrol.com") == "tier1"


def test_only_business_wire_may_have_its_http_links_upgraded(rules):
    assert [d for d, o in rules.outlets.items() if o.https_links] == ["businesswire.com"]


def test_no_outlet_names_an_extractor_that_is_not_run(rules):
    assert all(set(o.extract) <= {"jsonld", "trafilatura"} for o in rules.outlets.values())
    assert [o.extract for o in rules.outlets.values() if o.domain == "moneycontrol.com"] == [("jsonld", "trafilatura")]


def test_known_label_and_alias_lookups_work_on_the_real_names(rules):
    assert rules.domain_of_label("ET Markets") == "economictimes.indiatimes.com"
    assert rules.outlet_key("m.economictimes.com") == "economictimes.indiatimes.com"
    assert rules.domain_of_label("BusinessLine") == "thehindubusinessline.com"
    assert rules.is_opinion("seekingalpha.com", "/article/1") and not rules.is_opinion("seekingalpha.com", "/news/1")
    assert rules.wire_of_name("Press Trust of India") == "PTI" and rules.is_promotional_provider(
        "Zacks Investment Research"
    )
