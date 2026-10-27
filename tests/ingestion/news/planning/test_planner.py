"""NP3b: the feed plan is a pure function of the company list, the discovery file and the salt."""

from __future__ import annotations

import hashlib
import json

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.article.keys import WRAPPER
from fno.ingestion.news.feeds import FEED_ID, MAX_FEEDS, parse_feed_list
from fno.ingestion.news.planning import planner as planner_module
from fno.ingestion.news.planning.planner import FeedPlanError, plan_feeds
from fno.ingestion.news.planning.query_id import normalise_query, planned_feed_id
from tests.ingestion.news.planning.helpers import SALT, companies, company, discovery

ALPHA, BETA, GAMMA = company("ZZA", "Zzalpha", True), company("ZZB", "Zzbeta", True), company("ZZC", "Zzgamma")


def ids_of(plan) -> dict[str, str]:
    """feed id -> url of a plan."""
    return {f["id"]: f["url"] for f in json.loads(plan.data)["feeds"]}


def test_the_plan_lists_the_publisher_feeds_the_broad_queries_and_a_query_for_each_targeted_company_only():
    plan = plan_feeds(companies(ALPHA, BETA, GAMMA), discovery(), SALT)
    assert (plan.broad, plan.targeted, plan.publisher, plan.total) == (2, 2, 1, 5)
    feeds = {f["id"]: f for f in json.loads(plan.data)["feeds"]}
    assert feeds["feed-01"]["kind"] == "publisher" and sum(f["kind"] == WRAPPER for f in feeds.values()) == 4
    assert not any("Zzgamma" in f["url"] for f in feeds.values())  # not targeted: no query of its own


def test_the_plan_is_a_feed_list_every_reader_accepts_and_it_keeps_the_salt():
    plan = plan_feeds(companies(ALPHA), discovery(), SALT)
    parsed = parse_feed_list(plan.data, 1)
    assert parsed.salt == SALT and len(parsed.feeds) == plan.total
    assert all(FEED_ID.match(f.feed_id) for f in parsed.feeds)


def test_a_query_is_url_encoded_so_a_name_cannot_add_or_change_a_parameter():
    plan = plan_feeds(companies(company("ZZX", "Zz & Co&hl=evil#frag", True)), discovery(broad=[]), SALT)
    (url,) = [u for i, u in ids_of(plan).items() if i.startswith("q-")]
    assert url.startswith("https://search.svc.example/rss/search?") and "&hl=evil" not in url and "#" not in url
    assert url.count("hl=") == 1


def test_the_same_query_has_the_same_id_however_the_list_is_ordered_or_extended():
    first = ids_of(plan_feeds(companies(ALPHA, BETA), discovery(), SALT))
    reordered = ids_of(plan_feeds(companies(BETA, ALPHA), discovery(broad=["Zzsector news", "zzmarket outlook"]), SALT))
    more = ids_of(plan_feeds(companies(company("ZZN", "Zznew", True), ALPHA, BETA), discovery(), SALT))
    assert first == reordered and set(first) <= set(more) and len(more) == len(first) + 1


def test_case_and_spacing_do_not_make_a_different_query_and_a_repeated_query_is_planned_once():
    plan = plan_feeds(companies(ALPHA), discovery(broad=["Zz  Market", "zz market", " ZZ MARKET "]), SALT)
    assert plan.broad == 1
    assert normalise_query(" Zz   MARKET ") == "zz market"


def test_a_planned_id_is_keyed_with_the_private_salt_so_a_guessed_name_cannot_be_confirmed_from_the_poll_log():
    feed_id = planned_feed_id(SALT, WRAPPER, "Zzalpha zzstock")
    plain = "q-" + hashlib.sha256(f"{WRAPPER}\0zzalpha zzstock".encode()).hexdigest()[:8]
    assert feed_id != plain
    assert planned_feed_id("t" * 32, WRAPPER, "Zzalpha zzstock") != feed_id
    assert planned_feed_id(SALT, WRAPPER, "ZZALPHA   zzstock") == feed_id


def test_two_different_queries_that_share_an_id_are_refused_and_nothing_is_planned(monkeypatch):
    monkeypatch.setattr(planner_module, "planned_feed_id", lambda salt, kind, query: "q-00000000")
    with pytest.raises(FeedPlanError) as caught:
        plan_feeds(companies(ALPHA, BETA), discovery(), SALT)
    assert str(caught.value) == codes.FEED_PLAN_COLLISION


def test_an_id_used_before_with_another_kind_is_refused():
    feed_id = planned_feed_id(SALT, WRAPPER, "zzmarket outlook")
    with pytest.raises(FeedPlanError) as caught:
        plan_feeds(companies(ALPHA), discovery(), SALT, kinds_ever={feed_id: "publisher"})
    assert str(caught.value) == codes.FEED_PLAN_KIND_CONFLICT
    plan_feeds(companies(ALPHA), discovery(), SALT, kinds_ever={feed_id: WRAPPER})  # the same kind is fine


def test_new_and_dropped_ids_are_counted_against_the_previous_list():
    first = plan_feeds(companies(ALPHA, BETA), discovery(), SALT)
    second = plan_feeds(companies(ALPHA), discovery(), SALT, previous_ids=ids_of(first))
    assert (second.new, second.dropped) == (0, 1)
    assert plan_feeds(companies(ALPHA), discovery(), SALT).new == second.total


def test_a_plan_the_feed_list_checks_would_refuse_is_never_returned():
    many = [company(f"ZZ{n}", f"Zzname{n}", True) for n in range(MAX_FEEDS + 1)]
    with pytest.raises(FeedPlanError) as caught:
        plan_feeds(companies(*many), discovery(), SALT)
    assert str(caught.value) == codes.FEED_PLAN_INVALID
