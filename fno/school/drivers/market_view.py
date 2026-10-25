"""The slot snapshot as the desk's risk types see it (story MS-P1e), so D2's `CandidateBuilder` and C2's cost model
price the school's structures. Only two-sided valid quotes enter, at their mid: a leg without one is not listed."""

from dataclasses import dataclass
from datetime import date

from ...risk.inputs import ContractQuote, Market
from ..constants import OptionKind
from ..contracts.snapshot import ContractKey, SlotSnapshot

UNUSED_IV = 1.0  # `ContractQuote` demands an implied volatility; entry prices and the maximum loss never read it
NO_RATE = 0.0  # likewise: the rate and futures only matter to Black-76 stress, which the school does not run


@dataclass(frozen=True)
class SnapshotMarket:
    market: Market
    keys: dict[str, ContractKey]  # the risk contract name -> the snapshot's key
    touch: dict[str, tuple[float, float]]  # contract name -> (bid, ask)

    def key_of(self, contract: str) -> ContractKey:
        return self.keys[contract]


def contract_name(key: ContractKey) -> str:
    return f"{key.expiry.isoformat()}:{key.strike:g}:{key.kind}"


def snapshot_market(snapshot: SlotSnapshot, expiry: date) -> SnapshotMarket:
    quotes, keys, touch = {}, {}, {}
    for key, quote in snapshot.quotes.items():
        if key.expiry != expiry or not quote.two_sided:
            continue
        name = contract_name(key)
        quotes[name] = ContractQuote(key.strike, str(OptionKind(key.kind)), expiry, quote.mid, UNUSED_IV)
        keys[name], touch[name] = key, (quote.bid, quote.ask)
    return SnapshotMarket(Market(snapshot.session, snapshot.spot, NO_RATE, quotes, {}), keys, touch)
