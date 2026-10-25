"""Each expiry's outcome (story section 2, judges 452 and 452.1): NSE's final settlement price is the authority, G13b's
official closes the cross-check.

- E7's reader (`NseFinalSettlement`) reads the UDiFF files (from 2024) and needs every expiring row to agree.
- The old-format files (2019 to 5 Jul 2024) are read by `LegacyFileSettlement`, behind E7's interface: the expiring
  index future's `SETTLE_PR` is the index's final settlement price; an option row must carry the same price or 0
  (2019's files leave it 0), else the expiry is refused. Measured on real files, 22 Oct 2026: futures and options
  agree in 2021, 2023 and 2024; options read 0 on 31 Jan 2019.
- `FirstSettlement` asks each in turn: the first with a file decides (E7 first)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from ..constants import INDEX_FUTURE, INDEX_OPTION
from ..desk.settlement import FinalSettlement, SettlementError, SettlementPrices
from ..fo_bhavcopy import read_fo_file
from ..storage.raw_library import RawFileLibrary
from ..storage.raw_source import NseLegacyFoSource
from .constants import CLOSE_MISMATCH, NO_CLOSE_CHECK, NOT_SETTLED_YET, PAISA, REFUSED

NO_FUTURE = "no expiring index future traded on the expiry day for {what}"
OPTIONS_DISAGREE = "an expiring option's settle price is neither the future's nor 0 for {what}: {prices}"
DIFFERS = "settlement {settle} and official close {close} differ"
NOT_SETTLED, NO_CLOSE = "no settlement file yet", "no official close to cross-check"


class LegacyFileSettlement(SettlementPrices):
    def __init__(self, library: RawFileLibrary):
        self.library = library

    def final_settlement(self, underlying: str, expiry: date) -> FinalSettlement | None:
        path = NseLegacyFoSource.path_for(expiry)
        found = self.library.get(path)
        if found.data is None:
            return None
        rows = [r for r in read_fo_file(NseLegacyFoSource.filename_for(expiry), found.data)
                if r["TckrSymb"] == underlying and r["XpryDt"] == expiry.isoformat()]  # fmt: skip
        what = f"{underlying} {expiry} in {path}"
        futures = {float(r["SttlmPric"]) for r in rows if r["FinInstrmTp"] == INDEX_FUTURE and r["SttlmPric"]}
        if len(futures) != 1 or not min(futures) > 0:
            raise SettlementError(NO_FUTURE.format(what=what))
        price = futures.pop()
        options = {float(r["SttlmPric"] or 0) for r in rows if r["FinInstrmTp"] == INDEX_OPTION}
        if not options <= {price, 0.0}:
            raise SettlementError(OPTIONS_DISAGREE.format(what=what, prices=sorted(options)))
        return FinalSettlement(underlying, expiry, price, path, hashlib.sha256(found.data).hexdigest())


class FirstSettlement:
    """`(label, settlement)` from the first reader that has the expiry day's file; None when none has it."""

    def __init__(self, readers: Sequence[tuple[str, SettlementPrices]]):
        self.readers = readers

    def final_settlement(self, underlying: str, expiry: date) -> tuple[str, FinalSettlement] | None:
        for label, reader in self.readers:
            found = reader.final_settlement(underlying, expiry)
            if found is not None:
                return label, found
        return None


@dataclass(frozen=True)
class Settled:
    """One expiry's outcome: `price` is None when it is left out, and `problem` says why."""

    underlying: str
    expiry: date
    price: float | None
    source: str | None
    close: float | None
    problem: str | None

    @property
    def usable(self) -> bool:
        return self.price is not None

    @property
    def outcome(self) -> str:
        """What the report counts: the settlement's source when used, else why it was left out."""
        if self.usable:
            return self.source if self.problem is None else f"{self.source} ({NO_CLOSE_CHECK})"
        if self.problem == NOT_SETTLED:
            return NOT_SETTLED_YET
        return CLOSE_MISMATCH if self.source is not None else REFUSED


def settle(underlying: str, expiry: date, prices: FirstSettlement,
           close: Callable[[str, date], float | None]) -> Settled:  # fmt: skip
    official = close(underlying, expiry)
    try:
        found = prices.final_settlement(underlying, expiry)
    except SettlementError as exc:
        return Settled(underlying, expiry, None, None, official, str(exc))
    if found is None:
        return Settled(underlying, expiry, None, None, official, NOT_SETTLED)
    label, final = found
    if official is not None and abs(final.price - official) >= PAISA:
        return Settled(underlying, expiry, None, label, official, DIFFERS.format(settle=final.price, close=official))
    return Settled(underlying, expiry, final.price, label, official, None if official is not None else NO_CLOSE)
