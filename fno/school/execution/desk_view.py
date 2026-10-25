"""The school's slot snapshot and legs as E4 sees them (story MS-P1d), so E4's `price_leg`, E4c/E4d's `entry_problems`,
`FillMaker` and `closing_quotes` price school fills unchanged: one pricing rule for the desk and the school.

A school contract is named `<underlying><expiry YYYYMMDD><CE|PE><strike>` (e.g. `BANKNIFTY20261123PE50000`): the
underlying is every letter before the first digit, as `fno.contract_symbols.underlying_of` reads it, and two roads on
one index name the same contract the same way. The snapshot gives no provider symbol and no quote time (Groww gives
none), so every quote is `quote_age_unknown`, as A4 records it."""

from dataclasses import dataclass

from ...desk.pricing import DeskLeg
from ...desk.snapshot import ExecutionQuote, ExecutionSnapshot
from ...research_engine.structures import BOUGHT, SOLD, Leg
from ..constants import SIDE_BUY
from ..contracts.decisions import LegSpec
from ..contracts.snapshot import ContractKey, SlotQuote, SlotSnapshot
from .quote_rules import LIVE, QuoteRules

NOT_VALID = "not valid by A4's rule (no trade today)"


def contract_symbol(underlying: str, key: ContractKey) -> str:
    strike = str(int(key.strike)) if key.strike == int(key.strike) else repr(float(key.strike))
    return f"{underlying}{key.expiry:%Y%m%d}{key.kind}{strike}"


def desk_leg(underlying: str, leg: LegSpec) -> DeskLeg:
    side = BOUGHT if leg.side == SIDE_BUY else SOLD
    return DeskLeg(contract_symbol(underlying, leg.key), leg.key.expiry, Leg(leg.key.strike, str(leg.key.kind), side))


def signed_units(underlying: str, legs: tuple[LegSpec, ...], lot: int) -> dict[str, int]:
    """Contract -> units held (long +, short -), as E1's ledger counts them; a contract named twice adds up."""
    units: dict[str, int] = {}
    for leg in legs:
        contract = contract_symbol(underlying, leg.key)
        units[contract] = units.get(contract, 0) + (1 if leg.side == SIDE_BUY else -1) * leg.lots * lot
    return units


@dataclass(frozen=True)
class SchoolLeg:
    """One proposal or position leg with its desk form and its units (lots x the road day's lot)."""

    spec: LegSpec
    desk: DeskLeg
    units: int


def school_legs(underlying: str, legs: tuple[LegSpec, ...], lot: int) -> tuple[SchoolLeg, ...]:
    """In E4's order: every protective (bought) leg first, then the sold legs, each group as given."""
    built = [SchoolLeg(leg, desk_leg(underlying, leg), leg.lots * lot) for leg in legs]
    return tuple(sorted(built, key=lambda leg: not leg.desk.protective))


def execution_snapshot(snapshot: SlotSnapshot, underlying: str, rules: QuoteRules = LIVE) -> ExecutionSnapshot:
    """The road's verified capture as E4's execution snapshot: same ID, hash and times; quotes with A4's validity and
    their sizes as `rules` pass them."""
    quotes = {(key.expiry, float(key.strike), str(key.kind)): _quote(underlying, key, quote, rules)
              for key, quote in snapshot.quotes.items()}  # fmt: skip
    return ExecutionSnapshot(snapshot.session, snapshot.snapshot_id, snapshot.sha256, "", snapshot.started_at,
                             snapshot.finished_at, True, quotes)  # fmt: skip


def size_unmeasured(snapshot: SlotSnapshot, underlying: str, rules: QuoteRules) -> frozenset[str]:
    """The contracts `rules` refuse for an unmeasured size alone (none under practice rules)."""
    return frozenset(contract_symbol(underlying, key) for key, quote in snapshot.quotes.items()
                     if rules.size_not_measured(quote))  # fmt: skip


def _quote(underlying: str, key: ContractKey, quote: SlotQuote, rules: QuoteRules) -> ExecutionQuote:
    bid_size, ask_size = rules.sizes(quote)
    return ExecutionQuote(contract_symbol(underlying, key), key.expiry, float(key.strike), str(key.kind), quote.bid,
                          quote.ask, bid_size, ask_size, quote.valid, "" if quote.valid else NOT_VALID,
                          True)  # fmt: skip
