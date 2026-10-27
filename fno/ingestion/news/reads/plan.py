"""What order a read pass uses, and why (NP8). Two private files can reorder the pass: the company list (to tag) and the
owner's materiality terms. Both only change the ORDER of reads: neither changes what is archived or how anything is
stored. So, deliberately unlike the version 2 cluster run (where the list shapes archived grouping and a bad list
STOPS the run), here a bad file DEGRADES:

- **not configured** (never used by any pass): newest first, green. Nothing to alert.
- **used before and now missing, rolled back, edited in place (`news/pin.py`), damaged, or the store unreadable**:
  newest first, the run goes RED with the alert (loud, never silent) and NO pass note is written, so the pin does not
  move and the next pass still compares with the last good note. Reads go on.
- both files usable: material first, and the versions and SHA-256 used go into the pass note."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fno.ingestion.news import codes
from fno.ingestion.news.companies.model import CompanyListSource
from fno.ingestion.news.companies.parse import CompanyListError
from fno.ingestion.news.materiality.terms import MaterialityError, MaterialTerms
from fno.ingestion.news.pin import pin_violation
from fno.ingestion.news.reads.order import MATERIAL_FIRST, MaterialFirst, NewestFirst, ReadOrder
from fno.ingestion.news.reads.pass_note import PassNote, PassNotes
from fno.ingestion.news.reads.report import ReadReport
from fno.ingestion.news.tagging.dictionary import NameDictionary
from fno.ingestion.news.tagging.tagger import Tagger


class MaterialitySource(Protocol):
    def terms(self) -> MaterialTerms: ...


@dataclass(frozen=True)
class ReadPlan:
    order: ReadOrder
    note: PassNote | None = None  # the versions this pass used; only a material-first pass has one


@dataclass(frozen=True)
class _Spec:
    missing: str
    rolled_back: str
    damaged: str
    unavailable: str


COMPANIES = _Spec(
    codes.COMPANY_LIST_MISSING,
    codes.COMPANY_LIST_ROLLED_BACK,
    codes.COMPANY_LIST_DAMAGED,
    codes.COMPANY_LIST_UNAVAILABLE,
)
MATERIALITY = _Spec(
    codes.MATERIALITY_MISSING, codes.MATERIALITY_ROLLED_BACK, codes.MATERIALITY_DAMAGED, codes.MATERIALITY_UNAVAILABLE
)


class ReadPlanner:
    def __init__(self, companies: CompanyListSource, materiality: MaterialitySource, notes: PassNotes):
        self.companies, self.materiality, self.notes = companies, materiality, notes

    def plan(self, report: ReadReport) -> ReadPlan:
        try:
            last = self.notes.last()
        except Exception:  # noqa: BLE001 - a damaged note or a store error: the pin cannot be checked; only the code is kept
            report.reject(codes.PASS_NOTE_UNREADABLE)
            return ReadPlan(NewestFirst())
        # both files are always tried, so a pass reports every problem it finds
        companies = self._use(self.companies.companies, COMPANIES, last.companies_version if last else 0,
                              last.companies_sha256 if last else "", report)  # fmt: skip
        terms = self._use(self.materiality.terms, MATERIALITY, last.materiality_version if last else 0,
                          last.materiality_sha256 if last else "", report)  # fmt: skip
        if companies is None or terms is None:
            return ReadPlan(NewestFirst())
        tagger = Tagger(NameDictionary(companies))
        note = PassNote(MATERIAL_FIRST, 0, 0, 0, terms.version, terms.sha256, companies.version, companies.sha256)
        return ReadPlan(MaterialFirst(tagger, terms), note)

    @staticmethod
    def _use(load, spec: _Spec, last_version: int, last_sha256: str, report: ReadReport):
        try:
            found = load()
        except (CompanyListError, MaterialityError) as refused:
            if str(refused) != spec.missing or last_version:  # never configured is fine; used before and gone is not
                report.reject(str(refused))
            return None
        except Exception:  # noqa: BLE001 - a store error may name a path; only the code is kept
            report.reject(spec.unavailable)
            return None
        refusal = pin_violation(found.version, found.sha256, last_version, last_sha256, spec.rolled_back, spec.damaged)
        if refusal:
            report.reject(refusal)
            return None
        return found
