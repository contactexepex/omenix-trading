"""Readers of NSE's capital-market, delivery, listing and index files (``fno/shared/nse_files/nse_files.py``):
small inline samples parse to the documented records, wrong layouts raise ``BadFile``."""

from __future__ import annotations

from datetime import date

import pytest

from fno.shared.fo_bhavcopy import BadFile
from fno.shared.nse_files.nse_files import (
    EquityBar,
    read_delivery,
    read_equity_bhavcopy,
    read_equity_list,
    read_fo_rows,
    read_index_figures,
    read_nifty500_list,
)

CM_CSV = (
    b"TradDt,TckrSymb,SctySrs,ClsPric,HghPric,LwPric,TtlTradgVol,OpnPric\n"
    b"2026-10-12,RELIANCE,EQ,2550.50,2575.00,2540.00,1234567,2545.00\n"
    b"2026-10-12,YESBANK,BE,18.25,18.80,18.10,9876543,18.40\n"
    b"2026-10-12,NIFTYBEES,ETF,250.00,251.00,249.00,5000,250.50\n"  # not EQ/BE, must be skipped
)

DELIVERY_CSV = (
    b"SYMBOL, SERIES, DELIV_PER\n"
    b"RELIANCE, EQ, 55.12\n"
    b"YESBANK, BE, 40.00\n"
    b"ODDONE, EQ, -\n"  # NSE writes "-" where it has no figure
)

EQUITY_LIST_CSV = (
    b"SYMBOL,NAME OF COMPANY\nRELIANCE,Reliance Industries Limited\nTCS,Tata Consultancy Services Limited\n"
)

NIFTY500_CSV = b"Company Name,Industry,Symbol\nReliance Industries,Energy,RELIANCE\nTCS,IT,TCS\n"

INDEX_FIGURES_CSV = (
    b"Index Name,Closing Index Value,P/E,P/B,Div Yield\n"
    b"Nifty 50,22100.00,21.5,4.1,1.3\n"
    b"Nifty Bank,48250.00,18.2,-,1.0\n"
)

FO_ROWS_CSV = (
    b"TradDt,FinInstrmTp,TckrSymb,XpryDt,StrkPric,OptnTp,ClsPric\n2026-10-12,IDO,NIFTY,2026-10-30,22000,CE,350.25\n"
)


def test_read_equity_bhavcopy_keeps_only_eq_and_be() -> None:
    bars = read_equity_bhavcopy(CM_CSV, "cm.csv")
    assert len(bars) == 2
    assert {b.symbol for b in bars} == {"RELIANCE", "YESBANK"}
    reliance = next(b for b in bars if b.symbol == "RELIANCE")
    assert reliance == EquityBar(date(2026, 10, 12), "RELIANCE", "EQ", 2550.50, 2575.00, 2540.00, 1234567, 2545.00)


def test_read_delivery_none_for_missing_figure() -> None:
    delivery = read_delivery(DELIVERY_CSV, "delivery.csv")
    assert delivery == {"RELIANCE": 55.12, "YESBANK": 40.00, "ODDONE": None}


def test_read_equity_list_and_nifty500() -> None:
    assert read_equity_list(EQUITY_LIST_CSV, "list.csv")["RELIANCE"] == "Reliance Industries Limited"
    assert read_nifty500_list(NIFTY500_CSV, "n500.csv") == {"RELIANCE": "Energy", "TCS": "IT"}


def test_read_index_figures() -> None:
    figures = read_index_figures(INDEX_FIGURES_CSV, "idx.csv")
    assert figures["Nifty 50"].close == 22100.00
    assert figures["Nifty 50"].pe == 21.5
    assert figures["Nifty Bank"].pb is None  # "-" becomes None


def test_read_fo_rows_raw() -> None:
    rows = read_fo_rows(FO_ROWS_CSV, "fo.csv")
    assert rows[0]["TckrSymb"] == "NIFTY"
    assert rows[0]["OptnTp"] == "CE"


def test_wrong_layout_raises_badfile() -> None:
    with pytest.raises(BadFile):
        read_equity_bhavcopy(b"not,the,right,columns\n1,2,3,4\n", "cm.csv")
    with pytest.raises(BadFile):
        read_index_figures(b"nope\n1\n", "idx.csv")
