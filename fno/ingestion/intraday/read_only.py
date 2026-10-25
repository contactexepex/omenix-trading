"""The only Groww object the 15-minute recorder holds (story A16, criterion 10): an allow-list over the SDK client.

The client `growwapi.GrowwAPI` can place, modify and cancel orders (design 6.6: "a key that can trade"). The recorder
needs five read calls and a few constants, so this wrapper lets exactly those through and refuses every other name
before it reaches the SDK. The client itself is built (and signed in, after 06:00 IST each day) by `GrowwProvider`;
the wrapper is made around it in the composition root only. A guard, not a sandbox: it makes a trading call
impossible by mistake and visible in review."""

from __future__ import annotations

from collections.abc import Callable

READ_CALLS = frozenset({"get_quote", "get_option_chain", "get_expiries", "get_contracts", "get_historical_candles"})
CONSTANTS = frozenset(
    {"EXCHANGE_NSE", "SEGMENT_CASH", "SEGMENT_FNO", "CANDLE_INTERVAL_MIN_1", "CANDLE_INTERVAL_MIN_15"}  # 15: A16b
)
ALLOWED = READ_CALLS | CONSTANTS


class ReadOnlyViolation(AttributeError):
    """A name outside the allow-list was asked for; nothing reached the SDK."""


class ReadOnlyGroww:
    __slots__ = ("__client",)

    def __init__(self, client: Callable[[], object]):
        object.__setattr__(self, "_ReadOnlyGroww__client", client)  # called on each use: Groww's token renews daily

    def __getattr__(self, name: str):
        if name not in ALLOWED:
            raise ReadOnlyViolation(f"{name} is not a read call the recorder may use")
        return getattr(self.__client(), name)

    def __setattr__(self, name: str, value) -> None:
        raise ReadOnlyViolation("the read-only client cannot be changed")
