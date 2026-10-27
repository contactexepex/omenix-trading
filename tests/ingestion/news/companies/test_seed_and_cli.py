"""NP3a: the seed from NSE's archived lists (hand-made bytes in NSE's real layouts) and the command that writes it."""

from __future__ import annotations

import json
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.companies import cli as seed_cli
from fno.ingestion.news.companies import wiring
from fno.ingestion.news.companies.parse import parse_company_list
from fno.ingestion.news.companies.seed import build_seed, clean_name
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore
from fno.ingestion.storage.snapshot_source import EquityListSource, FoLotSizeSource, Nifty500ListSource

LOTS = (
    b"UNDERLYING                          ,SYMBOL    ,OCT-26     ,NOV-26\n"
    b"NIFTY BANK                          ,BANKNIFTY ,30         ,30\n"
    b"NIFTY 50                            ,NIFTY     ,75         ,75\n"
    b"Symbol                              ,Symbol    ,           ,\n"
    b"APOLLO HOSPITALS ENTER. L           ,APOLLOHOSP,125        ,125\n"
    b"ITC LTD                             ,ITC       ,1600       ,1600\n"
    b"ZZONLYMASTER CORP LTD               ,ZZMASTER  ,100        ,100\n"
)
EQUITY = (
    b"SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\n"
    b"APOLLOHOSP,Apollo Hospitals Enterprise Limited,EQ,06-OCT-2008,5,1,INE000000001,5\n"
    b"ITC,ITC Limited,EQ,06-OCT-2008,1,1,INE000000002,1\n"
)
NIFTY500 = (
    b"Company Name,Industry,Symbol,Series,ISIN Code\n"
    b"Zzextra Industries Ltd.,Capital Goods,ZZEXTRA,EQ,INE000000003\n"
    b"Apollo Hospitals Enterprise Ltd.,Healthcare,APOLLOHOSP,EQ,INE000000001\n"
)


def seeded(lots=LOTS, equity=EQUITY, n500=NIFTY500):
    seed = build_seed(lots, equity, n500)
    return seed, {c["symbol"]: c for c in json.loads(seed.data)["companies"]}


def test_the_universe_is_the_master_stocks_plus_the_nifty_500_and_the_indices_are_kept_apart():
    seed, by_symbol = seeded()
    assert (seed.stocks, seed.indices) == (4, 2) and set(by_symbol) == {
        "APOLLOHOSP",
        "ITC",
        "ZZMASTER",
        "ZZEXTRA",
        "BANKNIFTY",
        "NIFTY",
    }
    assert by_symbol["BANKNIFTY"]["kind"] == "index" and by_symbol["ITC"]["kind"] == "stock"


def test_the_name_comes_from_the_equity_list_then_the_nifty_500_and_only_last_from_the_abbreviated_master():
    _, by_symbol = seeded()
    assert (
        by_symbol["APOLLOHOSP"]["name"] == "Apollo Hospitals Enterprise"
    )  # not the master's "Apollo Hospitals Enter. L"
    assert by_symbol["ZZEXTRA"]["name"] == "Zzextra Industries"  # nifty 500 only
    assert by_symbol["ZZMASTER"]["name"] == "Zzonlymaster Corp"  # the master's own, cleaned


def test_a_short_all_capital_name_stays_capital_and_a_long_one_is_title_cased():
    assert (
        clean_name("ITC LTD") == "ITC"
        and clean_name("TRENT LTD") == "TRENT"
        and clean_name("MOTILAL OSWAL FIN LTD") == "Motilal Oswal Fin"
    )
    assert clean_name("ABB India Ltd.") == "ABB India" and clean_name("  Tata  Motors Limited ") == "Tata Motors"


def test_the_four_index_underlyings_get_their_public_names_and_nothing_else_has_an_alias():
    _, by_symbol = seeded()
    assert by_symbol["BANKNIFTY"]["aliases"] == ["Bank Nifty", "Nifty Bank"]
    assert all("aliases" not in c for c in by_symbol.values() if c["kind"] == "stock")


def test_two_symbols_with_one_cleaned_name_do_not_collide_the_second_keeps_its_full_form():
    equity = EQUITY + b"ZZDUP,Itc Limited,EQ,06-OCT-2008,1,1,INE000000009,1\n"
    lots = LOTS + b"ZZDUP LTD                           ,ZZDUP     ,10         ,10\n"
    seed, by_symbol = seeded(lots, equity)
    assert seed.renamed == 1 and by_symbol["ZZDUP"]["name"] != by_symbol["ITC"]["name"]
    assert parse_company_list(seed.data, 1).companies  # and the whole file passes the checks a consumer applies


def test_the_seed_is_deterministic_and_passes_the_list_checks():
    first, second = build_seed(LOTS, EQUITY, NIFTY500), build_seed(LOTS, EQUITY, NIFTY500)
    assert first.data == second.data and len(parse_company_list(first.data, 1).companies) == 6


def test_the_master_alone_is_enough_and_a_file_that_is_not_the_master_is_refused():
    assert build_seed(LOTS, None, None).stocks == 3
    with pytest.raises(ValueError):
        build_seed(b"SYMBOL,NAME\nA,B\n", None, None)


# ---- the command ----------------------------------------------------------------------------------------------------


class World:
    def __init__(self, tmp_path: Path, monkeypatch):
        self.drive = LocalFolderStore(tmp_path / "drive")
        self.raw, self.config = AreaStore(self.drive, "raw"), AreaStore(self.drive, "config")
        monkeypatch.setattr(wiring, "build_owner_drive", lambda env=None: self.drive)
        today = datetime.now(UTC).date()
        self.raw.put(FoLotSizeSource.path_for(today), LOTS)
        self.raw.put(EquityListSource.path_for(today), EQUITY)
        self.raw.put(Nifty500ListSource.path_for(today), NIFTY500)
        self.lines: list[str] = []

    def run(self, apply: bool) -> int:
        return seed_cli.cmd_seed_companies(Namespace(apply=apply), out=self.lines.append)


def test_without_apply_nothing_is_written_and_the_line_is_counts_only(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    assert world.run(False) == 0 and world.config.checksums("companies") == {}
    assert world.lines == ["news seed-companies (report only): stocks 4, indices 2, names given their full form 0"]
    assert not any(name in world.lines[0] for name in ("APOLLO", "Apollo", "ITC", "ZZ"))


def test_with_apply_the_first_version_is_written_and_a_second_seed_is_refused(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    assert world.run(True) == 0 and list(world.config.checksums("companies")) == ["companies-v1.json"]
    assert len(parse_company_list(world.config.get("companies/companies-v1.json"), 1).companies) == 6
    assert world.run(True) == 1 and world.lines[-1] == f"news seed-companies stopped: {codes.COMPANY_LIST_EXISTS}"


def test_a_missing_master_is_a_fixed_code(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    for path in world.drive.folder.rglob("fo_mktlots.csv"):
        path.unlink()
    assert world.run(True) == 1 and world.lines == [f"news seed-companies stopped: {codes.SEED_SOURCE_MISSING}"]


def test_an_unexpected_error_prints_only_its_class(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    for path in world.drive.folder.rglob("fo_mktlots.csv"):
        path.write_bytes(b"SYMBOL,NAME\nZZSECRET,Zzsecret Name\n")
    assert world.run(False) == 1 and world.lines == [f"news seed-companies stopped: {codes.UNEXPECTED} ValueError"]


def test_no_company_or_discovery_list_is_ever_in_the_repository():
    root = Path(__file__).resolve().parents[4]
    ignored = {".git", "__pycache__"}
    found = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and not ignored & set(p.parts)
             and (p.name.startswith(("companies-v", "discovery-v")) and p.suffix == ".json")]  # fmt: skip
    assert found == []
