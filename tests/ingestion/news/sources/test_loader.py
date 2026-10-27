"""NP1: a rules file with a mistake in it is refused with a sentence that names it; nothing is silently ignored."""

from __future__ import annotations

import pytest

from fno.ingestion.news.sources.loader import SourceRulesError, build_source_rules, load_source_rules


def doc(**changes):
    base = {"domains": {"a.com": {"tier": "tier1", "names": ["A News"]}, "b.com": {"tier": "tier2"}}}
    base.update(changes)
    return base


def refused(document, fragment):
    with pytest.raises(SourceRulesError, match=fragment):
        build_source_rules(document)


def test_a_good_document_loads():
    rules = build_source_rules(
        doc(wires={"W": {"names": ["W Staff"], "domains": ["w.com"]}}, promotional={"text": ["ad"]})
    )
    assert set(rules.outlets) == {"a.com", "b.com"} and rules.wires[0].name == "W"


@pytest.mark.parametrize("bad", [None, [], "text", {}, {"domains": {}}, {"domains": None}])
def test_a_document_without_domains_is_refused(bad):
    refused(bad, "non-empty `domains`")


def test_an_unknown_key_is_refused_wherever_it_is_so_a_typo_is_never_ignored():
    refused(doc(selection={"x": 1}), "unknown key.*top level.*selection")
    refused({"domains": {"a.com": {"tier": "tier1", "fech": False}}}, "unknown key.*a.com.*fech")
    refused(doc(wires={"W": {"nmaes": []}}), "unknown key.*wire W")
    refused(doc(promotional={"domain": []}), "unknown key.*promotional")


@pytest.mark.parametrize("name", ["A.com", "https://a.com", "a.com/news", "a.com:80", "a", "a b.com", "é.com", 5, None])
def test_a_domain_that_is_not_a_lower_case_host_name_is_refused(name):
    refused({"domains": {name: {"tier": "tier1"}}}, "not a lower-case host name")


@pytest.mark.parametrize("tier", ["tier3", "unlisted", "Tier1", None, 1])
def test_a_tier_that_is_not_a_listed_tier_is_refused(tier):
    refused({"domains": {"a.com": {"tier": tier}}}, "tier must be one of")


def test_a_flag_that_is_not_true_or_false_is_refused():
    refused({"domains": {"a.com": {"tier": "tier1", "fetch": "no"}}}, "`fetch` must be true or false")
    refused({"domains": {"a.com": {"tier": "tier1", "https_links": 1}}}, "`https_links` must be true or false")


def test_an_extractor_omenix_does_not_run_is_refused():
    refused(
        {"domains": {"a.com": {"tier": "tier1", "extract": ["jsonld", "newspaper"]}}}, "extractor omenix does not run"
    )
    assert build_source_rules({"domains": {"a.com": {"tier": "tier1", "extract": ["jsonld", "trafilatura"]}}})


def test_same_as_must_name_another_listed_main_domain():
    refused({"domains": {"a.com": {"tier": "tier1", "same_as": "a.com"}}}, "same_as must name another listed domain")
    refused({"domains": {"a.com": {"tier": "tier1", "same_as": "zzz.com"}}}, "same_as must name another listed domain")
    chain = {
        "a.com": {"tier": "tier1", "same_as": "b.com"},
        "b.com": {"tier": "tier1", "same_as": "c.com"},
        "c.com": {"tier": "tier1"},
    }
    refused({"domains": chain}, "no chains")


def test_a_name_two_outlets_claim_is_refused_even_when_only_case_differs():
    refused(
        {"domains": {"a.com": {"tier": "tier1", "names": ["Mint"]}, "b.com": {"tier": "tier1", "names": [" mint. "]}}},
        "claimed by both",
    )


def test_a_wire_or_promotional_entry_with_a_bad_domain_or_pattern_is_refused():
    refused(doc(wires={"W": {"domains": ["NOT A HOST"]}}), "wire W domains")
    refused(doc(promotional={"domains": ["https://x.com"]}), "promotional domains")
    refused(doc(promotional={"text": ["(unclosed"]}), "not a regular expression")
    refused(doc(promotional={"providers": "Zacks"}), "expected a list")


def test_a_file_that_is_missing_or_not_yaml_is_refused_without_its_text(tmp_path):
    with pytest.raises(SourceRulesError, match="cannot be read"):
        load_source_rules(tmp_path / "missing.yaml")
    broken = tmp_path / "broken.yaml"
    broken.write_text("domains: [unclosed")
    with pytest.raises(SourceRulesError, match="cannot be read"):
        load_source_rules(broken)


def test_a_repeated_key_is_refused_at_every_level_so_a_second_fetch_can_never_make_an_outlet_fetchable(tmp_path):
    cases = {
        "repeated fetch": "domains:\n  bseindia.com: {tier: primary, fetch: false, fetch: true}\n",
        "repeated outlet": "domains:\n  bseindia.com: {tier: primary, fetch: false}\n  bseindia.com: {tier: primary}\n",
        "repeated top key": "domains:\n  a.com: {tier: tier1}\ndomains:\n  b.com: {tier: tier1}\n",
        "repeated wire": "domains:\n  a.com: {tier: tier1}\nwires:\n  W: {names: [x]}\n  W: {names: [y]}\n",
    }
    for text in cases.values():
        file = tmp_path / "rules.yaml"
        file.write_text(text)
        with pytest.raises(SourceRulesError, match="repeated key"):
            load_source_rules(file)
    good = tmp_path / "good.yaml"
    good.write_text("domains:\n  a.com: {tier: tier1, fetch: false}\n")
    assert load_source_rules(good).may_fetch("a.com") is False
