"""Safety laws (story 3.3): only these stop a paper trade. A law reads; it never resizes or changes a proposal.
Law 6 ("no record, no trade") is the fill port's seal check (`FillPort.enter`), not a `SafetyLaw`: a law sees no
seal."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

from ..constants import RefusalReason
from .decisions import OpenPosition, Proposal
from .snapshot import SlotSnapshot


@dataclass(frozen=True)
class AccountView:
    """What a law may read of one driver version's account at the slot (read-only)."""

    driver_id: str
    capital: float
    cash: float
    equity: float  # cash plus open positions marked at this slot's valid quotes
    equity_high: float  # the highest equity since the account opened (or since its brake was last lifted)
    loss_since_previous_slot: float  # realised plus marked, rupees, zero or more
    opened_this_session: tuple[OpenPosition, ...]
    open_positions: tuple[OpenPosition, ...]
    brake_engaged_on: date | None  # set when equity first fell `brake_rs` below its high; held until a review lifts it
    brake_lifted_on: date | None  # the latest monthly review row that lifted this driver's brake


@dataclass(frozen=True)
class LawResult:
    law: str
    passed: bool
    reason: RefusalReason | None  # set exactly when refused
    limit: float | None = None
    value: float | None = None
    note: str = ""  # a plain label for the record, e.g. "margin not checked: no data"; never changes `passed`

    def __post_init__(self):
        if self.passed == (self.reason is not None):
            raise ValueError("a refusal names its reason; a pass names none")


@runtime_checkable
class SafetyLaw(Protocol):
    name: str

    def check(self, proposal: Proposal, account: AccountView, snapshot: SlotSnapshot, session: date) -> LawResult:
        """Pass at the limit, refuse beyond it; an unusable input refuses (fails closed)."""
