"""Composition root of the feed plan (NP3b): the concrete stores. Everything private is read from and written to the
`config` area of the Drive: the company list, the discovery file and the feed lists."""

from __future__ import annotations

import os
import secrets

from fno.ingestion.news import codes
from fno.ingestion.news.companies.private_file import PrivateCompanyFile
from fno.ingestion.news.feeds import FEEDS_FOLDER, FeedListError, PrivateFeedLists
from fno.ingestion.news.planning.discovery import PrivateDiscoveryFile
from fno.ingestion.news.planning.planner import FeedPlan, plan_feeds
from fno.ingestion.news.wiring import CONFIG_AREA
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.wiring import OWNER_UPLOAD_SETTINGS, build_owner_drive

SALT_BYTES = 16


def next_feed_list_name(names) -> str:
    numbers = [int(n[len("feeds-v") : -len(".json")]) for n in names if n.startswith("feeds-v") and n.endswith(".json")]
    return f"{FEEDS_FOLDER}/feeds-v{max(numbers, default=0) + 1}.json"


def plan_next_feed_list(apply: bool, env=os.environ) -> FeedPlan:
    """Plan from the newest company list and discovery file; write the next `feeds-vN.json` only with `apply`. The salt
    of the newest feed list is kept (it keeps every planned id stable); the first list gets a fresh random one."""
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to plan the feeds")
    config = AreaStore(drive, CONFIG_AREA)
    companies = PrivateCompanyFile(config).companies()
    discovery = PrivateDiscoveryFile(config).plan()
    lists = PrivateFeedLists(config)
    try:
        newest = lists.latest()
        salt, previous = newest.salt, [f.feed_id for f in newest.feeds]
        kinds = lists.kinds_ever_listed()
    except FeedListError as missing:
        if str(missing) != codes.FEED_LIST_MISSING:
            raise
        salt, previous, kinds = secrets.token_hex(SALT_BYTES), [], {}
    plan = plan_feeds(companies, discovery, salt, previous, kinds)
    if apply:
        config.put(next_feed_list_name(config.checksums(FEEDS_FOLDER)), plan.data)
    return plan
