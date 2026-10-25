"""The only feed object the A16h probe holds: an allow-list over `growwapi.GrowwFeed` (story A16h). The feed is built
from the full trading client and can also read the account (order and position updates), so this wrapper lets through
exactly the eleven market-data names and refuses every other name before it reaches the SDK. Built in the composition
root only (`feed_wiring.py`). A guard, not a sandbox: an account read or a trading call cannot happen by mistake."""

from __future__ import annotations

FEED_CALLS = frozenset({
    "subscribe_ltp", "subscribe_market_depth", "subscribe_index_value", "get_ltp", "get_market_depth",
    "get_index_value", "get_all_feed", "consume", "unsubscribe_ltp", "unsubscribe_market_depth",
    "unsubscribe_index_value",
})  # fmt: skip
# Named so the test can show each is refused (judge 499); the allow-list alone already refuses them.
ACCOUNT_CALLS = frozenset({
    "subscribe_fno_order_updates", "subscribe_fno_position_updates", "subscribe_equity_order_updates",
    "get_fno_order_update", "get_fno_position_update", "get_equity_order_update", "unsubscribe_fno_order_updates",
    "unsubscribe_fno_position_updates", "unsubscribe_equity_order_updates",
})  # fmt: skip


class FeedViolation(AttributeError):
    """A name outside the allow-list was asked for; nothing reached the feed."""


class ReadOnlyFeed:
    __slots__ = ("__feed",)

    def __init__(self, feed: object):
        object.__setattr__(self, "_ReadOnlyFeed__feed", feed)

    def __getattr__(self, name: str):
        if name not in FEED_CALLS:
            raise FeedViolation(f"{name} is not a market-data call the feed probe may use")
        return getattr(self.__feed, name)

    def __setattr__(self, name: str, value) -> None:
        raise FeedViolation("the read-only feed cannot be changed")
