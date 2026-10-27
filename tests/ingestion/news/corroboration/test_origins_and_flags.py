"""NP6b: how many independent places a cluster's story came from (invented outlets and agencies only)."""

from __future__ import annotations

import itertools

from fno.ingestion.news.corroboration import model
from fno.ingestion.news.corroboration.origins import corroborate
from fno.ingestion.news.origins.origin import BYLINE, DOMAIN, PROVIDER, TITLE
from fno.ingestion.news.tagging.tagger import Tag
from fno.ingestion.news.view import ArticleView


def view(key, outlet="pub-a.example", **changes) -> ArticleView:
    base = dict(
        key=key, url=f"https://{outlet}/a/{key}", host=outlet, tier="tier1", listed=True, opinion=False, wire="",
        wire_via="", outlet=outlet, promotional=False, tag=Tag(), material=False, access="",
    )  # fmt: skip
    return ArticleView(**{**base, **changes})


READ = {"access": "full"}


def flags(*views) -> tuple[str, ...]:
    return corroborate(views).flags


def test_articles_of_one_agency_are_one_origin_whichever_outlet_carries_them():
    result = corroborate([
        view("a", "pub-a.example", wire="AgencyA", wire_via=DOMAIN),
        view("b", "pub-b.example", wire="AgencyA", wire_via=BYLINE),
        view("c", "pub-c.example", wire="AgencyB", wire_via=PROVIDER),
    ])  # fmt: skip
    assert [g.label for g in result.groups] == ["wire:AgencyA", "wire:AgencyB"]
    assert result.groups[0].keys == ("a", "b") and result.independent_origins == 2


def test_articles_of_one_outlet_are_one_origin_and_an_agency_label_beats_the_outlet():
    result = corroborate([view("a", **READ), view("b", **READ), view("c", "pub-b.example", **READ)])
    assert [g.label for g in result.groups] == ["outlet:pub-a.example", "outlet:pub-b.example"]
    assert result.groups[0].keys == ("a", "b") and result.independent_origins == 2
    assert corroborate([view("a", wire="AgencyA", wire_via=DOMAIN)]).groups[0].label == "wire:AgencyA"


def test_a_promotional_an_opinion_and_an_unlisted_article_never_count():
    for change in ({"promotional": True}, {"opinion": True}, {"listed": False, "tier": "unlisted"}):
        result = corroborate([view("a", **READ, **change)])
        assert result.independent_origins == 0 and not result.groups[0].countable, change
    mixed = corroborate([view("a", **READ, promotional=True), view("b", **READ)])
    assert mixed.independent_origins == 1  # one countable article is enough for its group


def test_a_countable_article_is_verified_by_a_read_or_by_an_agency_proved_by_more_than_its_title():
    for access in ("full", "partial", "paywalled"):
        assert corroborate([view("a", access=access)]).independent_origins == 1, access
    for access in ("", "blocked", "not_html"):
        assert corroborate([view("a", access=access)]).independent_origins == 0, access
    for via in (DOMAIN, PROVIDER, BYLINE):
        assert corroborate([view("a", wire="AgencyA", wire_via=via)]).independent_origins == 1, via
    titled = corroborate([view("a", wire="AgencyA", wire_via=TITLE)])
    assert titled.independent_origins == 0 and titled.unverified_origins == 1


def test_each_flag_fires_on_exactly_its_rule_and_in_a_fixed_order():
    assert flags(view("a", **READ), view("b", "pub-b.example", **READ)) == ()
    assert flags(view("a", **READ)) == (model.SINGLE_SOURCE,)
    assert flags(view("a", **READ, promotional=True)) == (model.PROMOTIONAL_PROVIDER, model.NO_VETTED_ORIGIN)
    assert flags(view("a", **READ), view("b", "pub-b.example")) == (model.SINGLE_SOURCE, model.ORIGINS_UNVERIFIED)
    assert flags(view("a", **READ), view("b", "pub-b.example", opinion=True, **READ)) == (
        model.SINGLE_SOURCE, model.OPINION,
    )  # fmt: skip
    assert flags(view("a", listed=False, tier="unlisted")) == (
        model.NO_VETTED_ORIGIN, model.LOW_TIER_ONLY, model.UNREAD,
    )  # fmt: skip
    assert flags(view("a")) == (model.NO_VETTED_ORIGIN, model.ORIGINS_UNVERIFIED, model.UNREAD)
    assert flags() == (model.NO_VETTED_ORIGIN, model.LOW_TIER_ONLY, model.UNREAD)


def test_the_result_is_the_same_in_any_order_and_carries_the_reads_and_the_rules_it_came_from():
    views = [view("a", wire="AgencyA", wire_via=DOMAIN), view("b", "pub-b.example", **READ), view("c", "pub-c.example")]
    first = corroborate(views, "rules-1")
    for order in itertools.permutations(views):
        assert corroborate(order, "rules-1") == first
    assert first.reads_used == 1 and first.rules_version == "rules-1" and corroborate(views).rules_version == ""
