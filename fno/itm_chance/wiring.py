"""Composition root of story G13c: G13's records through the verified Drive cache, E7's settlement reader and the
legacy-file reader behind it, G13b's official closes for the cross-check, and O9's Drive data store for the report."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from ..desk.settlement import NseFinalSettlement
from ..price_distribution.method import method_sha256
from ..price_distribution.store import DriveDistributionStore
from ..price_ranges import wiring as g13b
from ..price_ranges.closes import Outcomes
from ..storage.data_wiring import DRIVE_CACHE_FOLDER, build_data_store
from ..storage.wiring import REPOSITORY, build_nse_fo_library, build_nse_legacy_fo_library, build_owner_drive
from .constants import SETTLED_FUTIDX, SETTLED_STTLM
from .settlement import FirstSettlement, LegacyFileSettlement, Settled, settle

WRITER = "itmchance"
NO_DRIVE = "set the four FNO_GDRIVE_* owner settings to use G13c's Drive data store"
PACKAGE = Path(__file__).resolve().parent
METHOD_FILES = tuple(PACKAGE / f"{name}.py" for name in ("calibration", "chances", "constants", "report", "rows",
                                                          "settlement"))  # fmt: skip


def methods() -> dict[str, str]:
    """G13's method (the records read) and G13c's own (the files that make the numbers)."""
    return {"g13": method_sha256(), "g13c": method_sha256(METHOD_FILES)}


def data_root() -> Path:
    return REPOSITORY / DRIVE_CACHE_FOLDER / "data"


def build_store(env=os.environ) -> DriveDistributionStore:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NO_DRIVE)
    return DriveDistributionStore(drive, build_data_store(WRITER, env=env))


def settlement_chain(udiff_library, legacy_library) -> FirstSettlement:
    """E7's UDiFF reader first; the old-format file's index future only where E7 has no file (judge 452.1)."""
    return FirstSettlement([(SETTLED_STTLM, NseFinalSettlement(udiff_library)),
                            (SETTLED_FUTIDX, LegacyFileSettlement(legacy_library))])  # fmt: skip


def build_settle():
    """`settle(underlying, expiry) -> Settled`: E7 first, the legacy file when E7 has none, G13b's close to check."""
    prices = settlement_chain(build_nse_fo_library(), build_nse_legacy_fo_library())
    outcomes = Outcomes(g13b.build_closes(g13b.build_tables(g13b.build_store())))

    def settled(underlying: str, expiry: date) -> Settled:
        return settle(underlying, expiry, prices, outcomes.close)

    return settled
