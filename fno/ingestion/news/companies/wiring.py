"""Composition root of the company list (NP3a): the only place that picks the concrete stores. The list is read from and
written to the private `config` area of the Drive; the NSE lists the seed is built from are read from the `raw` area."""

from __future__ import annotations

import os
from datetime import date, timedelta

from fno.ingestion.news import codes
from fno.ingestion.news.companies.model import CompanyListSource
from fno.ingestion.news.companies.parse import CompanyListError
from fno.ingestion.news.companies.private_file import COMPANIES_FOLDER, PrivateCompanyFile
from fno.ingestion.news.companies.seed import Seed, build_seed
from fno.ingestion.news.wiring import CONFIG_AREA
from fno.ingestion.storage.raw_store import AreaStore, RawFileStore
from fno.ingestion.storage.snapshot_source import EquityListSource, FoLotSizeSource, Nifty500ListSource
from fno.ingestion.storage.wiring import OWNER_UPLOAD_SETTINGS, RAW_AREA, build_owner_drive

LOOK_BACK_DAYS = 30
FIRST_FILE = f"{COMPANIES_FOLDER}/companies-v1.json"


class SeedFailed(Exception):
    """`str(error)` is one of the fixed codes."""


def build_company_list_source(env=os.environ) -> CompanyListSource:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to read the company list")
    return PrivateCompanyFile(AreaStore(drive, CONFIG_AREA))


def latest_copy(store: RawFileStore, source, today: date) -> bytes | None:
    """The newest archived copy of one NSE list within the look-back, or None."""
    for back in range(LOOK_BACK_DAYS + 1):
        data = store.get(source.path_for(today - timedelta(days=back)))
        if data is not None:
            return data
    return None


def seed_companies(apply: bool, today: date, env=os.environ) -> Seed:
    """Build the first list from the archived NSE lists; write it only with `apply`, and never over an existing list."""
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to seed the company list")
    config, raw = AreaStore(drive, CONFIG_AREA), AreaStore(drive, RAW_AREA)
    if config.checksums(COMPANIES_FOLDER):
        raise SeedFailed(codes.COMPANY_LIST_EXISTS)
    lots = latest_copy(raw, FoLotSizeSource, today)
    if lots is None:
        raise SeedFailed(codes.SEED_SOURCE_MISSING)
    try:
        seed = build_seed(lots, latest_copy(raw, EquityListSource, today), latest_copy(raw, Nifty500ListSource, today))
    except CompanyListError:
        raise SeedFailed(codes.COMPANY_LIST_INVALID) from None
    if apply:
        config.put(FIRST_FILE, seed.data)
    return seed
