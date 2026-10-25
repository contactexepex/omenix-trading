"""The dated lot of a road from A20a's archived NSE market-lot file (`fo_mktlots.csv`, one copy per session day)."""

import csv
from datetime import date

from ...research_data.fo_masters import BadFile, read_lot_sizes
from ...storage.raw_library import RawFileLibrary
from ...storage.snapshot_source import FoLotSizeSource
from ..constants import ClosureReason
from ..contracts.roads import DatedLot
from .ports import LotProblem

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def month_label(expiry: date) -> str:
    """The column NSE's lot file uses for an expiry month, e.g. `OCT-26` (never locale dependent)."""
    return f"{MONTHS[expiry.month - 1]}-{expiry:%y}"


UNAVAILABLE = LotProblem(ClosureReason.LOT_UNAVAILABLE)


class ArchivedLots:
    """Reads the session's own copy of the lot file from stored files; a session with no copy has no lot (a lot is
    never carried over from another day)."""

    def __init__(self, library: RawFileLibrary):
        self.library = library

    def lot(self, underlying: str, session: date, expiries: tuple[date, ...]) -> DatedLot | LotProblem:
        path = FoLotSizeSource.path_for(session)
        found = self.library.get(path).data
        if found is None:
            return UNAVAILABLE
        try:
            by_month = read_lot_sizes(found, FoLotSizeSource.FILENAME).get(underlying, {})
        except (BadFile, UnicodeDecodeError, csv.Error):
            return UNAVAILABLE
        units = {by_month.get(month_label(expiry)) for expiry in expiries}
        if None in units or min(units) <= 0:
            return UNAVAILABLE
        return LotProblem(ClosureReason.LOT_MISMATCH) if len(units) != 1 else DatedLot(units.pop(), path)
