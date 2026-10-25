"""The card's clock checks (stories T1 and T1f): `CardClocks` is the interface, so a rehearsal can swap in its own form
(REH1c's pattern) and the issuer never builds a server client it will not use. `ServerCardClocks` is the real run's:
the host clock against Slack's server time of the post and against each server's `Date`. A check that raises anything
is stored as unchecked by its error type, and named as a failure of the issue, never a stop after the post."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from ..server_clock import ServerClock, SkewCheck, check_server, skew_check, unchecked
from .posting import PostReceipt

SLACK, GITHUB = "Slack", "GitHub"
NOT_POSTED = "not posted"


@dataclass(frozen=True)
class ClockChecks:
    checks: tuple[SkewCheck, ...]
    failed: tuple[str, ...] = ()  # the servers whose check raised (T1f: exit 1), apart from a plain unchecked one


class CardClocks(ABC):
    @abstractmethod
    def check(self, receipt: PostReceipt, before: datetime, after: datetime) -> ClockChecks:
        """The host clock against each server, after the post; never raises."""


class ServerCardClocks(CardClocks):
    def __init__(self, servers: Sequence[ServerClock], host_now: Callable[[], datetime]):
        self.servers, self.host_now = tuple(servers), host_now

    def check(self, receipt: PostReceipt, before: datetime, after: datetime) -> ClockChecks:
        found = [guarded(SLACK, lambda: slack_check(receipt, before, after)),
                 *(guarded(s.name, lambda s=s: check_server(s, self.host_now)) for s in self.servers)]  # fmt: skip
        return ClockChecks(tuple(c for c, _ in found), tuple(c.server for c, raised in found if raised))


def slack_check(receipt: PostReceipt, before: datetime, after: datetime) -> SkewCheck:
    if receipt.server_time is None:
        return unchecked(SLACK, NOT_POSTED)
    return skew_check(SLACK, receipt.server_time, before, after)


def guarded(server: str, make: Callable[[], SkewCheck]) -> tuple[SkewCheck, bool]:
    """(the check, whether it raised): a refused or broken call is a stored, named miss, never a lost record."""
    try:
        return make(), False
    except Exception as error:  # noqa: BLE001 - the card is already out: its records must still be written
        return unchecked(server, type(error).__name__), True
