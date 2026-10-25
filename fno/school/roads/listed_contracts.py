"""The contracts NSE listed for a road's expiries, from the previous session's archived F&O file (no new NSE read).
The quality gate takes its scheduled legs from here: a strike the capture dropped is a leg observed and not passed."""

import zipfile
from collections.abc import Collection
from datetime import date, timedelta

from ...fo_bhavcopy import BadFile, read_fo_file
from ...quotes.expiry_listing import INDEX_OPTION, LOOKBACK_DAYS
from ...quotes.recorder import SPOT_BAND
from ...storage.raw_library import RawFileLibrary
from ...storage.raw_source import NseDailyFoSource
from ..constants import OptionKind
from ..contracts.snapshot import ContractKey
from ..quality.ports import ListingUnavailable


class NseListedContracts:
    def __init__(self, library: RawFileLibrary):
        self.library = library
        self._rows: dict[date, list[dict] | None] = {}

    def contracts(
        self, underlying: str, expiries: Collection[date], session: date, spot: float
    ) -> frozenset[ContractKey]:
        wanted = {expiry.isoformat() for expiry in expiries}
        rows = self._latest(session - timedelta(days=1))
        try:
            found = frozenset(
                ContractKey(date.fromisoformat(r["XpryDt"]), float(r["StrkPric"]), OptionKind(r["OptnTp"]))
                for r in rows
                if r["FinInstrmTp"] == INDEX_OPTION and r["TckrSymb"] == underlying and r["XpryDt"] in wanted
            )
            found = frozenset(k for k in found if spot * (1 - SPOT_BAND) <= k.strike <= spot * (1 + SPOT_BAND))
        except (KeyError, ValueError) as error:
            raise ListingUnavailable(f"{underlying} {session}: listing rows unreadable: {error}") from error
        if not found:
            raise ListingUnavailable(f"{underlying} {session}: the listing holds no contract for {sorted(wanted)}")
        return found

    def _latest(self, last_day: date) -> list[dict]:
        for back in range(LOOKBACK_DAYS):
            rows = self._file(last_day - timedelta(days=back))
            if rows is not None:
                return rows
        raise ListingUnavailable(f"no NSE F&O file in the {LOOKBACK_DAYS} days up to {last_day}")

    def _file(self, day: date) -> list[dict] | None:
        """The day's rows, or None for no file. The store is read outside the try: its own failures (an outage, a
        non-JSON Drive reply) propagate, and only an unreadable F&O file is a `ListingUnavailable`."""
        if day not in self._rows:
            data = self.library.get(NseDailyFoSource.path_for(day)).data
            try:
                self._rows[day] = None if data is None else read_fo_file(NseDailyFoSource.filename_for(day), data)
            except (BadFile, zipfile.BadZipFile, UnicodeDecodeError, ValueError) as error:
                raise ListingUnavailable(f"{day}: the F&O file is unreadable: {error}") from error
        return self._rows[day]
