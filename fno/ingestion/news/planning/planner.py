"""The feed planner (NP3b): a pure function from (the company list, the discovery file, the feed list's salt) to the
next feed list's bytes. Nothing is fetched and nothing is written here. The fetcher, Staging, the gate and the poll log
read the result as they read any feed list, so a new company list changes the plan at the next `plan-feeds`, not the
code.

Two checks make a re-plan safe: two different queries that hash to one id are refused (the id is the binding), and an id
that an earlier version listed with another kind is refused (changing a kind would give existing items new keys). The
result is parsed with the feed list's own checks before it is returned, so a plan every reader would refuse is never
written."""

from __future__ import annotations

import json
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from urllib.parse import urlencode

from fno.ingestion.news import codes
from fno.ingestion.news.article.keys import PUBLISHER, WRAPPER
from fno.ingestion.news.companies.model import CompanyList
from fno.ingestion.news.feeds import FeedListError, parse_feed_list
from fno.ingestion.news.planning.discovery import NAME_SLOT, DiscoveryPlan
from fno.ingestion.news.planning.query_id import normalise_query, planned_feed_id


class FeedPlanError(Exception):
    """`str(error)` is one of the fixed codes."""


@dataclass(frozen=True)
class FeedPlan:
    data: bytes
    broad: int
    targeted: int
    publisher: int
    new: int  # feeds whose id the previous list did not have
    dropped: int  # ids the previous list had that this plan no longer lists (their staged polls stay promotable)

    @property
    def total(self) -> int:
        return self.broad + self.targeted + self.publisher


def _search_url(discovery: DiscoveryPlan, query: str) -> str:
    params = dict(discovery.params)
    params[discovery.query_param] = query
    separator = "&" if "?" in discovery.search_url else "?"
    return discovery.search_url + separator + urlencode(params)


def _queries(companies: CompanyList, discovery: DiscoveryPlan) -> tuple[list[str], list[str]]:
    """(broad queries, targeted queries), each without repeats once normalised."""
    seen: set[str] = set()

    def fresh(query: str) -> bool:
        key = normalise_query(query)
        if key in seen:
            return False
        seen.add(key)
        return True

    broad = [q for q in discovery.broad if fresh(q)]
    own = (discovery.targeted_template.replace(NAME_SLOT, c.name) for c in companies.companies if c.targeted)
    return broad, [q for q in own if fresh(q)]


def plan_feeds(
    companies: CompanyList,
    discovery: DiscoveryPlan,
    salt: str,
    previous_ids: Collection[str] = (),
    kinds_ever: Mapping[str, str] | None = None,
) -> FeedPlan:
    """`previous_ids`: the ids of the newest existing list. `kinds_ever`: every id ever listed -> its kind."""
    kinds_ever = kinds_ever or {}
    broad, targeted = _queries(companies, discovery)
    entries = [{"id": i, "url": u, "kind": PUBLISHER} for i, u in discovery.publisher_feeds]
    by_id: dict[str, str] = {}
    for query in (*broad, *targeted):
        feed_id = planned_feed_id(salt, WRAPPER, query)
        if by_id.setdefault(feed_id, normalise_query(query)) != normalise_query(query):
            raise FeedPlanError(codes.FEED_PLAN_COLLISION)
        entries.append({"id": feed_id, "url": _search_url(discovery, query), "kind": WRAPPER})
    for entry in entries:
        if kinds_ever.get(entry["id"], entry["kind"]) != entry["kind"]:
            raise FeedPlanError(codes.FEED_PLAN_KIND_CONFLICT)
    data = json.dumps({"salt": salt, "feeds": entries}, sort_keys=True, separators=(",", ":")).encode()
    try:
        parse_feed_list(data, 1)
    except FeedListError:
        raise FeedPlanError(codes.FEED_PLAN_INVALID) from None
    ids = {e["id"] for e in entries}
    return FeedPlan(data, len(broad), len(targeted), len(discovery.publisher_feeds),
                    len(ids - set(previous_ids)), len(set(previous_ids) - ids))  # fmt: skip
