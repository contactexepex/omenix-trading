"""Dated terms (story MS-SIM-a, 7.1 item 3): the lot and the charges in force on a session, never today's."""

from collections.abc import Callable, Mapping
from datetime import date

from ...constants import PANEL_FORMAT_LEGACY
from ..contracts.roads import DatedLot
from .history.ports import DayChain

CircularLot = Callable[[str, date], int | None]
ChargesOn = Callable[[date], dict]
FILE_LOT, CIRCULAR_LOT = "NSE board lot in the archived file", "NSE circular schedule"


class DatedTerms:
    def __init__(self, circular_lot: CircularLot, charges_on: ChargesOn):
        self.circular_lot, self.charges_on = circular_lot, charges_on

    def lot(self, chain: DayChain, expiry: date) -> DatedLot | None:
        """NSE's board lot where that day's file states it. A legacy-format file states none, so only there the circular
        schedule is used (it ends with the legacy files); a current-format day with no stated lot, or an index with no
        schedule, gives None and the road is closed, never filled with a guess."""
        if chain.lots.get(expiry):
            return DatedLot(chain.lots[expiry], f"{FILE_LOT} ({chain.source}), {chain.session}")
        if chain.source != PANEL_FORMAT_LEGACY:
            return None
        scheduled = self.circular_lot(chain.underlying, expiry)
        return DatedLot(scheduled, f"{CIRCULAR_LOT}, {chain.session}") if scheduled else None

    def charges(self, session: date) -> Mapping[str, float]:
        return self.charges_on(session)
