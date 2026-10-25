"""Composition root of the 3 pm quote store (story A4b): Groww's raw quote files in the `raw` area of the owner's Drive
only, checked against their committed sidecars; sidecars, canonical markers and NSE's public chain in the repository.
Apart from `wiring.py`, which is at the 350-line limit; `wiring.build_quote_store` calls it, so its callers (G1 v2's
frozen capture among them) are unchanged."""

from __future__ import annotations

import os
from pathlib import Path

from ..quotes.drive_only_store import DriveOnlyQuoteStore
from ..quotes.recorder import DATASET as GROWW_QUOTE_DATASET
from .raw_store import AreaStore, LocalFolderStore, RawFileStore
from .wiring import OWNER_UPLOAD_SETTINGS, RAW_AREA, build_owner_drive


def build_drive_only_quote_store(
    folder: Path, env=os.environ, dataset: str = GROWW_QUOTE_DATASET
) -> DriveOnlyQuoteStore:
    """Drive is signed in to only when a raw quote file is first saved or read, so building the store needs no Drive
    (the forecast job's golden step, the NSE recorder and the tests build it without the settings). `dataset`: the Groww
    dataset whose quote files go to Drive (A4e: a named window has its own)."""

    def drive() -> RawFileStore | None:
        owner = build_owner_drive(env)
        return AreaStore(owner, RAW_AREA) if owner is not None else None

    settings = ", ".join(OWNER_UPLOAD_SETTINGS)
    return DriveOnlyQuoteStore(LocalFolderStore(folder), drive, dataset, settings)
