"""The first adapter of `CompanyListSource` (NP3a): `config/companies-vN.json` in the private config area of the Drive,
with the discipline of the feed list (`news/versioned.py`): the newest version is used, none older than one already
used, a version edited in place is skipped loudly. The list is the owner's private content: nothing here is ever
logged or committed."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from fno.ingestion.news import codes
from fno.ingestion.news.companies.model import CompanyList, CompanyListSource
from fno.ingestion.news.companies.parse import CompanyListError, parse_company_list
from fno.ingestion.news.versioned import ErrorCodes, VersionedFiles
from fno.ingestion.storage.raw_store import RawFileStore

COMPANIES_FOLDER = "companies"


class PrivateCompanyFile(CompanyListSource):
    def __init__(self, store: RawFileStore, lowest_version: int = 0, used: Mapping[int, str] | None = None):
        """`store`: the private config area (read only). `lowest_version`, `used`: as for the feed list."""
        self.files = VersionedFiles(
            store, COMPANIES_FOLDER, "companies",
            ErrorCodes(codes.COMPANY_LIST_MISSING, codes.COMPANY_LIST_ROLLED_BACK, codes.COMPANY_LIST_DAMAGED),
            CompanyListError,
        )  # fmt: skip
        self.lowest_version, self.used = lowest_version, used

    def companies(self) -> CompanyList:
        picked = self.files.latest(self.lowest_version, self.used)
        return replace(parse_company_list(picked.data, picked.version), sha256=picked.sha256)
