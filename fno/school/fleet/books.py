"""The two ledgers the fleet writes (story MS-P1j): the driver accounts (MS-P1d) and the ticket ledger (MS-P1f), each
with its read-only entries, and the one fill port both are filled through."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from ..contracts.accounts import AccountPort, FillPort, LedgerReader
from ..contracts.decisions import OpenPosition
from ..contracts.snapshot import ContractKey
from ..tickets.book import TicketBook

T = TypeVar("T")
EntryMids = Callable[[OpenPosition], dict[ContractKey, float]]  # the mids an entry met, from its sealed record


@dataclass(frozen=True)
class Books:
    accounts: AccountPort
    account_entries: LedgerReader
    tickets: TicketBook
    ticket_entries: LedgerReader
    fills: FillPort

    @property
    def stores(self) -> tuple[AccountPort, AccountPort]:
        """Every account store the fleet records into, the driver account first: each is opened by the session's
        view before any fill (an unviewed store refuses a record; the first ticket ever exposed it, SIM, 23 Oct)."""
        return self.accounts, self.tickets.ledger.store


class AccountUnreadable(RuntimeError):
    """A driver's account or ticket ledger could not be read or written: the session stops loudly, never as that
    driver's `driver_error` (it is not the driver's fault) and never silently (orchestrator's ruling e). Named by the
    driver and the error's class only."""

    def __init__(self, driver_id: str, cause: Exception):
        super().__init__(f"{driver_id} ({type(cause).__name__})")
        self.driver_id = driver_id


def account_call(driver_id: str, action: Callable[..., T], *args) -> T:
    """`action(*args)` on `driver_id`'s account or ticket ledger (a read or a record), any failure of which is
    `AccountUnreadable`."""
    try:
        return action(*args)
    except Exception as error:  # noqa: BLE001 - any store failure is the one named stop
        raise AccountUnreadable(driver_id, error) from error
