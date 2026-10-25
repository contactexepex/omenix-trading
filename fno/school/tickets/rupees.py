"""Rupees shown to the owner (327 items 1 and 10): only account trades whose fills the displayed size could serve.
A ticket's net measures the rule on that road and is never added; an outcome whose entry or exit was unservable
beside other accounts (`shared_size.allocate`) is left out and named. Every report sums through here."""

from collections.abc import Collection, Iterable
from dataclasses import dataclass

from ..contracts.accounts import FillResult
from ..contracts.records import OutcomeRecord


@dataclass(frozen=True)
class AccountNet:
    net: float
    left_out: tuple[str, ...]  # position IDs of account outcomes with an unservable fill


def account_net(outcomes: Iterable[OutcomeRecord],
                unservable: Collection[tuple[str, FillResult]] = ()) -> AccountNet:  # fmt: skip
    """`unservable`: (driver id, fill) pairs from `SizeAllocation.unservable_fills`."""
    trades = [outcome for outcome in outcomes if not outcome.is_ticket]
    shared = [o for o in trades if (o.driver_id, o.entry) in unservable or (o.driver_id, o.exit) in unservable]
    kept = [o for o in trades if o not in shared]
    return AccountNet(sum(o.net for o in kept), tuple(o.position_id for o in shared))
