"""NSE daily F&O file reader (``fno/shared/fo_bhavcopy.py``): both formats parse to one record shape, the shared
fields of the two formats match on a day both exist, and damaged files raise ``BadFile``."""

from __future__ import annotations

import io
import zipfile

import pytest

from fno.shared.fo_bhavcopy import (
    BadFile,
    csv_text,
    legacy_date,
    read_fo_file,
    read_index_closes,
    read_index_values,
)

UDIFF_NAME = "BhavCopy_NSE_FO_0_0_0_20261012_F_0000.csv.zip"
LEGACY_NAME = "fo12OCT2026bhav.csv.zip"

# A single NIFTY future row written in each format, same prices, so the shared fields must match exactly.
UDIFF_CSV = (
    "TradDt,BizDt,Sgmt,Src,FinInstrmTp,TckrSymb,XpryDt,StrkPric,OptnTp,OpnPric,HghPric,LwPric,ClsPric,LastPric,"
    "PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,NewBrdLotQty\n"
    "2026-10-12,2026-10-12,FO,NSE,IDF,NIFTY,2026-10-30,,,22000.00,22150.00,21950.00,22100.00,22105.00,21980.00,"
    "22100.00,22100.00,123450,500,98765,21800000000.00,4321,75\n"
)
LEGACY_CSV = (
    "INSTRUMENT,SYMBOL,EXPIRY_DT,STRIKE_PR,OPTION_TYP,OPEN,HIGH,LOW,CLOSE,SETTLE_PR,CONTRACTS,VAL_INLAKH,OPEN_INT,"
    "CHG_IN_OI,TIMESTAMP\n"
    "FUTIDX,NIFTY,30-OCT-2026,0,XX,22000.00,22150.00,21950.00,22100.00,22100.00,98765,218000.00,123450,500,"
    "12-OCT-2026\n"
)
INDEX_CLOSE_CSV = (
    "Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value\n"
    "Nifty 50,12-10-2026,22000.00,22200.00,21900.00,22100.00\n"
    "Nifty Bank,12-10-2026,48000.00,48400.00,47800.00,48250.00\n"
)


def _zip(member_name: str, csv_text_body: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member_name, csv_text_body)
    return buffer.getvalue()


def test_legacy_date_parsing() -> None:
    assert legacy_date("02-JAN-2019") == "2019-01-02"
    assert legacy_date("31-Jan-2019") == "2019-01-31"


def test_udiff_file_parses_to_records() -> None:
    rows = read_fo_file(UDIFF_NAME, _zip("BhavCopy.csv", UDIFF_CSV))
    assert len(rows) == 1
    row = rows[0]
    assert row["TckrSymb"] == "NIFTY"
    assert row["FinInstrmTp"] == "IDF"
    assert row["ClsPric"] == "22100.00"
    assert row["OpnIntrst"] == "123450"


def test_legacy_file_parses_and_fills_index_underlying() -> None:
    closes = read_index_closes(INDEX_CLOSE_CSV.encode("utf-8"))
    rows = read_fo_file(LEGACY_NAME, _zip("fo.csv", LEGACY_CSV), closes)
    assert len(rows) == 1
    row = rows[0]
    assert row["TckrSymb"] == "NIFTY"
    assert row["FinInstrmTp"] == "IDF"  # OPTIDX/FUTIDX mapped to UDiFF instrument codes
    assert row["TradDt"] == "2026-10-12"
    assert row["XpryDt"] == "2026-10-30"
    assert row["UndrlygPric"] == "22100.00"  # taken from the official index close


def test_shared_fields_match_across_formats() -> None:
    closes = read_index_closes(INDEX_CLOSE_CSV.encode("utf-8"))
    udiff = read_fo_file(UDIFF_NAME, _zip("BhavCopy.csv", UDIFF_CSV))[0]
    legacy = read_fo_file(LEGACY_NAME, _zip("fo.csv", LEGACY_CSV), closes)[0]
    for field in ("TradDt", "TckrSymb", "FinInstrmTp", "XpryDt", "ClsPric", "OpnIntrst", "ChngInOpnIntrst",
                  "OpnPric", "HghPric", "LwPric", "UndrlygPric"):  # fmt: skip
        assert udiff[field] == legacy[field], field


def test_read_index_closes_and_values() -> None:
    closes = read_index_closes(INDEX_CLOSE_CSV.encode("utf-8"))
    assert closes == {"Nifty 50": 22100.00, "Nifty Bank": 48250.00}
    values = read_index_values(INDEX_CLOSE_CSV.encode("utf-8"))
    assert values["Nifty 50"]["open"] == 22000.00
    assert values["Nifty 50"]["high"] == 22200.00
    assert values["Nifty 50"]["close"] == 22100.00


def test_damaged_zip_raises_badfile() -> None:
    with pytest.raises(BadFile):
        csv_text("broken.zip", b"not a real zip file at all")


def test_unknown_filename_raises_badfile() -> None:
    with pytest.raises(BadFile):
        read_fo_file("mystery_file.csv.zip", _zip("x.csv", UDIFF_CSV))


def test_empty_index_file_raises_badfile() -> None:
    with pytest.raises(BadFile):
        read_index_closes(b"Index Name,Closing Index Value\n")
