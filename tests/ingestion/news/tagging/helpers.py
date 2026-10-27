"""A small invented company list for the tagger tests: made-up names and symbols only."""

from __future__ import annotations

from fno.ingestion.news.companies.model import Company, CompanyList
from fno.ingestion.news.tagging.dictionary import NameDictionary
from fno.ingestion.news.tagging.tagger import Tagger

COMPANIES = (
    Company("ZZAL", "Zzalpha Holdings", aliases=("Zzalpha",)),
    Company("ZZBE", "Zzbeta Bank", aliases=("Zzbeta",)),
    Company("ZZGA", "Zzgamma Foods", exclusions=("Zzgamma Foods Lanka",)),
    Company("ZZDE", "Zzdelta"),
    Company("ZZLT", "Zz & Lt Works", aliases=("ZZ&LT",)),
    Company("ZZOM", "Zzomega", exclusions=("Zzomega Hospitality",)),
    Company("ZZAB", "Zzalpha Bank"),  # a longer name that starts like another company's
)
TAGGER = Tagger(NameDictionary(CompanyList(1, COMPANIES)))


def tag(title, summary=None, source=None):
    return TAGGER.tag(title, summary, source)
