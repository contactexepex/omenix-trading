"""The adapter that lets C2's rule classes check a school proposal unedited (story MS-P1d): C2's proposal, its book
(the driver version's own account, never another's) and the part of its market those rules read, built from the
school's types.

- Contracts are named as the school names them (`execution/desk_view.py`), so C2's bucket map reads the index.
- `SlotMarket` gives C2 what `MaxLossPerTrade`, the caps and `MarginRoom` read of its `Market`: the day and each
  contract's strike, type, expiry and mid. A mid comes only from this slot's snapshot of the contract's own index,
  at a valid two-sided quote; a contract without one raises C2's own `RiskInputError` when its mid is read, so the
  rule refuses (fails closed). Implied volatility, which C2's stress rules need, is not offered: the school runs none.
- C2's terms are MS-P1m's `RoadTradeTerms` (the structure code, its width, one lot count for every leg, the index,
  the one expiry, the legs and the units per lot, checked against the structure's shape), and C2's proposal and open
  trades are built from them by MS-P1m's factories, so C2's margin and C2's units read one source. A leg ratio, two
  expiries or a shape the code does not name is refused."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

from ...books.equity import AccountState
from ...nse_margins.road_trades import RoadTradeTerms, road_open_trade, road_proposal
from ...research_engine.structures import BOUGHT, SOLD, Leg
from ...risk.inputs import OpenTrade, RiskBook, RiskInputError, SessionTrade
from ...risk.inputs import Proposal as RiskProposal
from ..constants import SIDE_BUY, OptionKind, RoadCode
from ..contracts.decisions import LegSpec, OpenPosition, Proposal
from ..contracts.roads import ROADS_BY_CODE
from ..contracts.safety import AccountView
from ..contracts.snapshot import ContractKey, SlotSnapshot
from ..execution.desk_view import contract_symbol, signed_units

PROPOSAL_ID = "proposal"  # the proposal's trade ID inside C2's book: never a held position's ID


@dataclass(frozen=True)
class SlotQuoteView:
    strike: float
    kind: str
    expiry: date
    known_mid: float | None
    stale: bool = False  # C2 refuses a stale mark for a new trade; the school never offers one

    @property
    def mid(self) -> float:
        if self.known_mid is None:
            raise RiskInputError(f"no valid two-sided quote at this slot for {self.kind} {self.strike:g} {self.expiry}")
        return self.known_mid


class SlotMarket:
    """This slot's snapshots as the part of C2's `Market` the school's rules read."""

    def __init__(self, day: date, snapshots: Mapping[RoadCode, SlotSnapshot], contracts: Mapping[str, ContractKey]):
        self.day, self.contracts = day, dict(contracts)
        self.mids: dict[str, float] = {}
        for road, snapshot in snapshots.items():
            for key, quote in snapshot.quotes.items():
                if quote.mid is not None:
                    self.mids.setdefault(contract_symbol(ROADS_BY_CODE[road].underlying, key), quote.mid)

    def quote(self, contract: str) -> SlotQuoteView:
        if contract not in self.contracts:
            raise RiskInputError(f"no contract {contract} in this check")
        key = self.contracts[contract]
        return SlotQuoteView(key.strike, str(key.kind), key.expiry, self.mids.get(contract))


@dataclass(frozen=True)
class C2Inputs:
    proposal: RiskProposal
    book: RiskBook
    market: SlotMarket


def c2_inputs(proposal: Proposal, road: RoadCode, account: AccountView,
              snapshots: Mapping[RoadCode, SlotSnapshot], session: date) -> C2Inputs:  # fmt: skip
    """Raises `RiskInputError` for a proposal or a held position C2 cannot size."""
    contracts = _contracts(road, proposal.legs)
    for position in (*account.open_positions, *account.opened_this_session):
        contracts |= _contracts(position.road, position.legs)
    risk = _risk_proposal(PROPOSAL_ID, road, proposal.structure, proposal.legs, proposal.lot)
    return C2Inputs(risk, _book(account), SlotMarket(session, snapshots, contracts))


def _book(account: AccountView) -> RiskBook:
    # C2's rules the school runs read cash, marked equity and the reserves; `closed_equity` and `open_value` are read
    # only by C2's drawdown and reports, which the school does not run, so they carry the view's equity and its split.
    state = AccountState(account.capital, account.cash, account.equity, account.equity - account.cash, account.equity,
                         0.0, 0.0, len(account.open_positions), ())  # fmt: skip
    held = tuple(_open_trade(p) for p in account.open_positions)
    today = tuple(SessionTrade(p.position_id, ((_signed_units(p), p.entry_net),)) for p in account.opened_this_session)
    return RiskBook(account.driver_id, state, held, (), (), today)


def _open_trade(position: OpenPosition) -> OpenTrade:
    terms = road_terms(position.position_id, position.road, position.structure, position.legs, position.lot)
    return road_open_trade(position.position_id, terms, _contract_of, position.entry_net)


def _signed_units(position: OpenPosition) -> dict[str, int]:
    return signed_units(ROADS_BY_CODE[position.road].underlying, position.legs, position.lot)


def _risk_proposal(trade_id: str, road: RoadCode, structure: str, legs: tuple[LegSpec, ...], lot: int) -> RiskProposal:
    return road_proposal(trade_id, road_terms(trade_id, road, structure, legs, lot), _contract_of)


def road_terms(trade_id: str, road: RoadCode, structure: str, legs: tuple[LegSpec, ...], lot: int) -> RoadTradeTerms:
    """MS-P1m's terms of one school trade: its index, its one expiry, one unit per leg and its lots, checked against
    its structure's shape. C2's proposal and open trade are built from them by MS-P1m's factories, so the margin and
    the units can never disagree."""
    lots, expiries = {leg.lots for leg in legs}, {leg.key.expiry for leg in legs}
    if len(lots) != 1 or len(expiries) != 1:
        raise RiskInputError(f"{trade_id}: legs of {sorted(lots)} lots on {len(expiries)} expiries; C2 sizes one each")
    one_unit = tuple(_leg(leg) for leg in legs)
    underlying = ROADS_BY_CODE[road].underlying
    return RoadTradeTerms(structure, structure_width(legs), lots.pop(), underlying, expiries.pop(), one_unit, lot)


def _contract_of(underlying: str, expiry: date, leg: Leg) -> str:
    return contract_symbol(underlying, ContractKey(expiry, leg.strike, OptionKind(leg.kind)))


def _leg(leg: LegSpec) -> Leg:
    return Leg(leg.key.strike, str(leg.key.kind), BOUGHT if leg.side == SIDE_BUY else SOLD)


def structure_width(legs: Iterable[LegSpec]) -> float:
    """The widest gap between a bought and a sold strike of one option type (0 for a bought-only structure)."""
    legs = tuple(legs)
    gaps = [abs(b.key.strike - s.key.strike) for b in legs for s in legs
            if b.side == SIDE_BUY and s.side != SIDE_BUY and b.key.kind == s.key.kind]  # fmt: skip
    return max(gaps, default=0.0)


def _contracts(road: RoadCode, legs: Iterable[LegSpec]) -> dict[str, ContractKey]:
    underlying = ROADS_BY_CODE[road].underlying
    return {contract_symbol(underlying, leg.key): leg.key for leg in legs}
