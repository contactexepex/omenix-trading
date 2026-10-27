"""NP3a: the company-list file (a private content), its checks, and the adapter that finds the newest version."""

from __future__ import annotations

import hashlib
import json
import re

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.companies.model import CompanyListSource
from fno.ingestion.news.companies.parse import CompanyListError, parse_company_list
from fno.ingestion.news.companies.private_file import PrivateCompanyFile
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore

MARK = "Zzmark Holdings"  # a marker name: it must never appear in an error


def file_bytes(*companies: dict, **top) -> bytes:
    document = {"format": 1, "companies": list(companies), **top}
    return json.dumps(document).encode()


def company(symbol="ZZMARK", name=MARK, **more) -> dict:
    return {"symbol": symbol, "name": name, **more}


def refused(data: bytes) -> str:
    with pytest.raises(CompanyListError) as caught:
        parse_company_list(data, 1)
    return str(caught.value)


def test_a_good_list_is_read_with_its_defaults():
    parsed = parse_company_list(
        file_bytes(company(), company("ZZTWO", "Zztwo Consultancy Services", aliases=["ZZTWO"])), 3
    )
    assert parsed.version == 3 and [c.symbol for c in parsed.companies] == ["ZZMARK", "ZZTWO"]
    first = parsed.companies[0]
    assert (first.aliases, first.exclusions, first.targeted, first.kind) == ((), (), False, "stock")


@pytest.mark.parametrize(
    "data",
    [
        b"not json", b"[]", b"{}", file_bytes(), file_bytes(company(), format=2), file_bytes(company(), extra=1),
        file_bytes(company("lower", "N")), file_bytes(company("A B", "N")), file_bytes(company("", "N")),
        file_bytes(company("A", ".")), file_bytes(company("A", " ")), file_bytes(company("A", "N", kind="fund")),
        file_bytes(company("A", "N", targeted="yes")), file_bytes(company("A", "N", surprise=1)),
        file_bytes({"symbol": "A"}), file_bytes(company("A", "N", aliases="x")),
        file_bytes(company("A", "N", aliases=[""])),
        file_bytes(company("A", "N", aliases=["..."])), file_bytes(company("A", "N" * 121)),
        file_bytes(company("A", "N"), company("A", "M")),  # a repeated symbol
        file_bytes(company("A", "Same Name"), company("B", " same name. ")),  # two companies, one name
        file_bytes(company("A", "Alpha", aliases=["Beta"]), company("B", "Beta")),  # an alias is another's name
    ],
)  # fmt: skip
def test_a_list_with_a_mistake_is_refused_with_one_fixed_code(data):
    assert refused(data) == codes.COMPANY_LIST_INVALID


@pytest.mark.parametrize(
    "pattern",
    [
        "(unclosed",
        "x" * 121,
        "(a+)+b",
        "(a|b)*c",
        "(?:a+){2,}",
        "(a)+",
        ".*.*.*.*.*.*Z",
        r"\w*\w*\w*\w*\w*\w*!",
        ".*.*.*Z",
        "a?a?a?a?a?aaaa",
        "x{2,}y{2,}z{2,}",
    ],
)
def test_an_exclusion_that_is_not_a_regex_or_could_run_for_ever_is_refused(pattern):
    assert refused(file_bytes(company(exclusions=[pattern]))) == codes.COMPANY_LIST_INVALID


@pytest.mark.parametrize(
    "pattern",
    ["Zzfoo Bar\\w*", "Zzbar (?:Lifespaces?|Holdings|Logistics)\\w*", "Zzfoo Hotels", "ZZ&Q (?:Finance|Tech)\\w*"],
)
def test_a_plain_name_pattern_with_a_word_tail_and_an_optional_letter_is_accepted(pattern):
    assert parse_company_list(file_bytes(company(exclusions=[pattern])), 1).companies[0].exclusions == (pattern,)


def test_the_caps_on_size_are_enforced():
    many = [company(f"S{n}", f"Name {n}") for n in range(2001)]
    assert refused(file_bytes(*many)) == codes.COMPANY_LIST_INVALID
    assert refused(file_bytes(company(aliases=[f"a{n}" for n in range(21)]))) == codes.COMPANY_LIST_INVALID
    assert refused(file_bytes(company(exclusions=[f"e{n}" for n in range(21)]))) == codes.COMPANY_LIST_INVALID


def test_a_refusal_never_names_a_symbol_a_name_or_a_pattern():
    for data in (
        file_bytes(company(kind="fund")),
        file_bytes(company(exclusions=["(zzmark+)+"])),
        file_bytes(company(), company()),
    ):
        text = refused(data)
        assert MARK not in text and "ZZMARK" not in text and "zzmark" not in text.lower()


# ---- the adapter ----------------------------------------------------------------------------------------------------


def config(tmp_path, **versions: bytes) -> AreaStore:
    store = AreaStore(LocalFolderStore(tmp_path / "drive"), "config")
    for version, data in versions.items():
        store.put(f"companies/companies-{version}.json", data)
    return store


def test_the_adapter_is_a_company_list_source_and_uses_the_newest_version(tmp_path):
    store = config(
        tmp_path,
        v1=file_bytes(company("A", "Old")),
        v2=file_bytes(company("B", "New")),
        v10=file_bytes(company("C", "Newest")),
    )
    source = PrivateCompanyFile(store)
    assert isinstance(source, CompanyListSource)
    listed = source.companies()
    assert listed.version == 10 and [c.symbol for c in listed.companies] == ["C"]


def test_no_list_is_a_fixed_code(tmp_path):
    with pytest.raises(CompanyListError, match=codes.COMPANY_LIST_MISSING):
        PrivateCompanyFile(config(tmp_path)).companies()


def test_a_newest_version_older_than_one_already_used_is_refused(tmp_path):
    with pytest.raises(CompanyListError, match=codes.COMPANY_LIST_ROLLED_BACK):
        PrivateCompanyFile(config(tmp_path, v1=file_bytes(company())), lowest_version=2).companies()


def test_a_version_edited_after_it_was_used_is_skipped_for_the_older_good_one(tmp_path):
    original, edited = file_bytes(company("A", "Alpha")), file_bytes(company("B", "Beta"))
    store = config(tmp_path, v1=file_bytes(company("O", "Older")), v2=edited)
    used = {2: hashlib.sha256(original).hexdigest()}  # version 2 had other bytes when it was used
    assert [c.symbol for c in PrivateCompanyFile(store, used=used).companies().companies] == ["O"]


def test_a_newest_version_that_is_invalid_stops_the_run_rather_than_falling_back(tmp_path):
    store = config(tmp_path, v1=file_bytes(company()), v2=b"broken")
    with pytest.raises(CompanyListError, match=codes.COMPANY_LIST_INVALID):
        PrivateCompanyFile(store).companies()


def test_no_exclusion_the_list_accepts_can_run_long_on_a_crafted_headline():
    import time

    pattern = r"Zzfoo (?:Alpha|Beta)\w*"  # the richest shape the grammar allows
    parse_company_list(file_bytes(company(exclusions=[pattern])), 1)
    start = time.monotonic()
    for text in ("Zzfoo Alpha" + "a" * 50_000, "Zzfoo Alpha " * 4_000):
        re.search(pattern, text)
    assert time.monotonic() - start < 1
