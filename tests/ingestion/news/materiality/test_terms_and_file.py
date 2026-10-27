"""NP5b: weighted material terms and their private versioned file (invented terms only)."""

from __future__ import annotations

import json

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.materiality.file import PrivateMaterialityFile
from fno.ingestion.news.materiality.terms import MaterialityError, MaterialTerms, parse_terms
from fno.ingestion.news.tagging.tagger import HIGH, LOW, Tag
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore


def document(*terms, **changes) -> bytes:
    body = {
        "format": 1,
        "terms": [{"pattern": p, "weight": w} for p, w in terms] or [{"pattern": "zzquarterly", "weight": 1}],
    }
    return json.dumps({**body, **changes}).encode()


TERMS = parse_terms(document(("zzquarterly results", 0.6), ("zzmerger", 1.0), ("zzprofit (?:warning|alert)", 0.5)), 3)
ONE = Tag(("ZZAL",), (), HIGH)


def test_a_headline_weighs_the_sum_of_the_terms_it_matches_each_counted_once():
    assert TERMS.weight("ZZQuarterly Results beat; zzquarterly results again") == pytest.approx(0.6)
    assert TERMS.weight("zzquarterly results and a zzprofit warning") == pytest.approx(1.1)
    assert TERMS.weight("nothing here") == 0 and TERMS.weight(None) == 0 and TERMS.version == 3


def test_a_headline_is_material_only_with_weight_one_or_more_and_exactly_one_high_confidence_company():
    assert TERMS.is_material("zzmerger talks", ONE)
    assert TERMS.is_material("zzquarterly results, zzprofit warning", ONE)  # 0.6 + 0.5
    assert not TERMS.is_material("zzquarterly results", ONE)  # 0.6 is under 1
    assert not TERMS.is_material(
        "zzmerger talks", Tag((), ("ZZAL", "ZZBE"), LOW)
    )  # several or low-confidence companies
    assert not TERMS.is_material("zzmerger talks", Tag())


def test_a_term_beyond_the_text_cap_is_not_seen():
    assert TERMS.weight("x " * 600 + "zzmerger") == 0


@pytest.mark.parametrize(
    "data",
    [
        b"not json", b"[]", b"{}", document(format=2), document(extra=1), document(terms=[]), document(("a*", 1)),
        document((".*.*x", 1)), document(("(unclosed", 1)), document(("zzmerger", 0)), document(("zzmerger", -1)),
        document(("zzmerger", 11)), document(("zzmerger", "1")), document(("zzmerger", True)),
        document(("zzmerger", 1), ("ZZMERGER", 2)),  # the same term twice
        json.dumps({"format": 1, "terms": [{"pattern": "zzmerger"}]}).encode(),
        json.dumps({"format": 1, "terms": [{"pattern": "zzmerger", "weight": 1, "x": 1}]}).encode(),
        json.dumps({"format": 1, "terms": [{"pattern": f"z{n}", "weight": 1} for n in range(201)]}).encode(),
    ],
)  # fmt: skip
def test_a_file_with_a_mistake_is_refused_with_one_fixed_code_and_no_text(data):
    with pytest.raises(MaterialityError) as caught:
        parse_terms(data, 1)
    assert str(caught.value) == codes.MATERIALITY_INVALID


def test_the_adapter_reads_the_newest_version_and_stops_on_a_missing_or_rolled_back_one(tmp_path):
    config = AreaStore(LocalFolderStore(tmp_path / "drive"), "config")
    with pytest.raises(MaterialityError) as missing:
        PrivateMaterialityFile(config).terms()
    assert str(missing.value) == codes.MATERIALITY_MISSING
    config.put("materiality/materiality-v1.json", document(("zzolder", 1)))
    config.put("materiality/materiality-v2.json", document(("zznewer", 1)))
    found = PrivateMaterialityFile(config).terms()
    assert found.version == 2 and found.weight("zznewer") == 1 and found.weight("zzolder") == 0
    with pytest.raises(MaterialityError) as rolled_back:
        PrivateMaterialityFile(config, lowest_version=3).terms()
    assert str(rolled_back.value) == codes.MATERIALITY_ROLLED_BACK


def test_a_materiality_file_is_never_in_the_repository():
    """What the repository walk can enforce: no private versioned file by name (NP3a does the same for companies)."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    ignored = {".git", "__pycache__"}
    found = [p.name for p in root.rglob("materiality-v*.json") if p.is_file() and not ignored & set(p.parts)]
    assert found == []


def test_the_empty_terms_object_weighs_nothing():
    assert MaterialTerms(()).weight("zzmerger") == 0 and not MaterialTerms(()).is_material("zzmerger", ONE)
