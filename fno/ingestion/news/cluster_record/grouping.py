"""What clustering algorithm version 2 needs besides the articles (NP6a): the owner's company list and the resolution
files of the window's Google News items. Both are read only. The rules, stated as the guarantee they are (NP6 plan,
judge 96 B2, B3):

- the same articles, the same resolution set and the same company list give the same bytes; a re-run of a closed
  window that sees other input is refused by the write-once rule and reported;
- **no company list at all** (`company_list_missing`) is a legitimate state: `companies_version` is 0 and no bar
  moves;
- **a list that exists but cannot be loaded or verified** (invalid, rolled back, damaged, or the store itself
  unreadable) STOPS the run with that code and writes nothing: never a silent fallback to an unmoved bar, which would
  record a quietly different grouping.
- a damaged resolution file also stops the run (`resolution_unreadable`); a missing one is just an item not resolved
  yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fno.ingestion.news import codes
from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.article.keys import WRAPPER
from fno.ingestion.news.cluster.prepare import GROUPER_VERSION, Preparer
from fno.ingestion.news.cluster.window import in_window
from fno.ingestion.news.cluster_record.cluster_file import ClusterFile
from fno.ingestion.news.companies.model import CompanyList, CompanyListSource
from fno.ingestion.news.companies.parse import CompanyListError
from fno.ingestion.news.resolve.resolution_file import Resolution, parse_resolution, resolution_path
from fno.ingestion.news.tagging.dictionary import NameDictionary
from fno.ingestion.news.tagging.tagger import Tagger
from fno.ingestion.storage.raw_store import RawFileStore


class GroupingBlocked(Exception):
    """`str(error)` is one of the fixed codes; the run writes nothing."""


@dataclass(frozen=True)
class GroupingInputs:
    preparer: Preparer
    companies_version: int
    resolutions_used: int
    companies_sha256: str = ""


class SymbolGrouping:
    version = GROUPER_VERSION

    def __init__(self, companies: CompanyListSource, record: RawFileStore):
        self.companies, self.record = companies, record

    def inputs(
        self, articles: tuple[Article, ...], as_of: datetime, previous: ClusterFile | None = None
    ) -> GroupingInputs:
        """`previous`: the latest earlier file of this version; its list is not to be gone behind or found changed."""
        companies = self._company_list(previous)
        resolutions = self._resolutions(articles, as_of)
        tagger = Tagger(NameDictionary(companies))
        return GroupingInputs(Preparer(tagger, resolutions), companies.version, len(resolutions), companies.sha256)

    def _company_list(self, previous: ClusterFile | None) -> CompanyList:
        try:
            companies = self.companies.companies()
        except CompanyListError as refused:
            if str(refused) == codes.COMPANY_LIST_MISSING and not (previous and previous.companies_version):
                return CompanyList(0, ())  # no list was ever used: version 0, no bar moves
            raise GroupingBlocked(str(refused)) from None  # a list used before is gone: a stop, not version 0
        except Exception:  # noqa: BLE001 - a store error may name a path; only the code is kept
            raise GroupingBlocked(codes.COMPANY_LIST_UNAVAILABLE) from None
        _refuse_going_behind(companies, previous)
        return companies

    def _resolutions(self, articles: tuple[Article, ...], as_of: datetime) -> dict[str, Resolution]:
        found = {}
        for article in articles:
            if article.kind != WRAPPER or not in_window(article, as_of):
                continue
            try:
                data = self.record.get(resolution_path(article.key))
                if data is not None:
                    found[article.key] = parse_resolution(data)
            except Exception:  # noqa: BLE001 - a damaged file or a store error: one code, nothing named
                raise GroupingBlocked(codes.RESOLUTION_UNREADABLE) from None
        return found


def _refuse_going_behind(companies: CompanyList, previous: ClusterFile | None) -> None:
    """The list this run reads against the one the last file used (NP7b; judge 100 N4, judge 101 B1).

    An older version is a rollback, and the same version with other bytes is a list edited in place (a version number
    alone would not show it). A newer version is simply a new list. Nothing to compare with before the first file, or
    after a run with no list."""
    if previous is None or not previous.companies_version:
        return
    if companies.version < previous.companies_version:
        raise GroupingBlocked(codes.COMPANY_LIST_ROLLED_BACK)
    if companies.version == previous.companies_version and companies.sha256 != previous.companies_sha256:
        raise GroupingBlocked(codes.COMPANY_LIST_DAMAGED)
