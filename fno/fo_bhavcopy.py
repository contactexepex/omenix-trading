"""Reads NSE's daily F&O files into one record format, whichever format the file is in.

NSE published the old format ("fo02JAN2019bhav.csv.zip") up to 5 July 2024 and the current UDiFF format
("BhavCopy_NSE_FO_..._F_0000.csv.zip") from 1 January 2024. Both carry the same contracts and prices: on the days both
exist every row and every shared field match exactly (tests/test_fo_bhavcopy.py, research/2026-10-12-legacy-format).
Records use the UDiFF column names. A field the old format does not carry is left empty, never guessed, except the
underlying price of index options, taken from NSE's official index close for that day (the same number UDiFF
reports). The original files are never changed.
"""

from __future__ import annotations

import csv
import io
import zipfile
import zlib
from abc import ABC, abstractmethod

from .constants import MONTH_CODES

COLUMNS = (
    "TradDt", "BizDt", "Sgmt", "Src", "FinInstrmTp", "TckrSymb", "XpryDt", "StrkPric", "OptnTp", "OpnPric", "HghPric",
    "LwPric", "ClsPric", "LastPric", "PrvsClsgPric", "UndrlygPric", "SttlmPric", "OpnIntrst", "ChngInOpnIntrst",
    "TtlTradgVol", "TtlTrfVal", "TtlNbOfTxsExctd", "NewBrdLotQty",
)  # fmt: skip
LEGACY_INSTRUMENTS = {"OPTIDX": "IDO", "OPTSTK": "STO", "FUTIDX": "IDF", "FUTSTK": "STF"}
LEGACY_NO_OPTION_TYPE = "XX"  # futures rows
INDEX_NAMES = {  # F&O symbol -> its name in NSE's index-close file
    "NIFTY": "Nifty 50",
    "BANKNIFTY": "Nifty Bank",
    "FINNIFTY": "Nifty Financial Services",
    "MIDCPNIFTY": "Nifty Midcap Select",
    "NIFTYNXT50": "Nifty Next 50",
}
LEGACY_FIELDS = {  # current column <- old column, copied as is
    "OpnPric": "OPEN", "HghPric": "HIGH", "LwPric": "LOW", "ClsPric": "CLOSE", "SttlmPric": "SETTLE_PR",
    "OpnIntrst": "OPEN_INT", "ChngInOpnIntrst": "CHG_IN_OI", "TtlTradgVol": "CONTRACTS",
}  # fmt: skip
RUPEES_PER_LAKH = 100_000


class BadFile(ValueError):
    """The file is damaged or not in a known format: never read it partly."""


CLOSE_COLUMN = "Closing Index Value"
INDEX_VALUE_COLUMNS = {"open": "Open Index Value", "high": "High Index Value", "low": "Low Index Value",
                       "close": CLOSE_COLUMN}  # fmt: skip


def legacy_date(text: str) -> str:
    """'02-JAN-2019' or '31-Jan-2019' -> '2019-01-02' (month names read without the computer's language settings)."""
    day, month, year = text.strip().split("-")
    return f"{year}-{MONTH_CODES.index(month.upper()) + 1:02d}-{int(day):02d}"


def csv_text(filename: str, data: bytes) -> str:
    """The CSV inside a zip (checksums verified) or a plain CSV."""
    if not filename.endswith(".zip"):
        return data.decode("utf-8-sig")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            if len(names) != 1 or archive.testzip() is not None:
                raise BadFile(f"{filename}: expected one intact CSV, found {names}")
            return archive.read(names[0]).decode("utf-8-sig")
    except (zipfile.BadZipFile, zlib.error, EOFError) as exc:
        raise BadFile(f"{filename}: damaged or not a zip ({exc})") from exc


def _index_rows(data: bytes, filename: str):
    """(index name, row) for each named row of NSE's daily index-close file."""
    for row in csv.DictReader(io.StringIO(csv_text(filename, data))):
        name = (row.get("Index Name") or "").strip()
        if name:
            yield name, row


def _value(row: dict, column: str) -> float | None:
    """A column's number; None where NSE prints nothing or "-"."""
    text = (row.get(column) or "").strip()
    return None if text in ("", "-") else float(text)


def _lenient(row: dict, column: str) -> float | None:
    """A column's number, None for anything else: one index's odd text (e.g. "NA") never voids the file's other rows;
    a reader that needs a value it finds None says so (A4h-2's "not in the official file")."""
    try:
        return _value(row, column)
    except ValueError:
        return None


def read_index_closes(data: bytes, filename: str = "index-close.csv") -> dict[str, float]:
    """Index name -> closing value, from NSE's daily index-close file."""
    closes = {name: _value(row, CLOSE_COLUMN) for name, row in _index_rows(data, filename)}
    closes = {name: close for name, close in closes.items() if close is not None}
    if not closes:
        raise BadFile(f"{filename}: no index closing values")
    return closes


def read_index_values(data: bytes, filename: str = "index-close.csv") -> dict[str, dict[str, float | None]]:
    """Index name -> its official open, high, low and close (None where NSE prints nothing or "-"), from NSE's daily
    index-close file (story A4h-2: the day range a list read is confirmed against)."""
    values = {name: {field: _lenient(row, column) for field, column in INDEX_VALUE_COLUMNS.items()}
              for name, row in _index_rows(data, filename)}  # fmt: skip
    if not any(found["close"] is not None for found in values.values()):
        raise BadFile(f"{filename}: no index closing values")
    return values


class FoFileFormat(ABC):
    """One format of NSE's daily F&O file."""

    @abstractmethod
    def recognises(self, filename: str) -> bool: ...

    @abstractmethod
    def records(self, rows: list[dict], index_closes: dict[str, float]) -> list[dict]:
        """The file's rows as records with the COLUMNS keys."""


class UdiffFormat(FoFileFormat):
    def recognises(self, filename: str) -> bool:
        return filename.startswith("BhavCopy_NSE_FO_")

    def records(self, rows: list[dict], index_closes: dict[str, float]) -> list[dict]:
        if rows and "TckrSymb" not in rows[0]:
            raise BadFile("UDiFF file without its columns")
        return [{c: (r.get(c) or "").strip() for c in COLUMNS} for r in rows]


class LegacyFormat(FoFileFormat):
    def recognises(self, filename: str) -> bool:
        return filename.startswith("fo") and filename.endswith("bhav.csv.zip")

    def records(self, rows: list[dict], index_closes: dict[str, float]) -> list[dict]:
        if rows and "INSTRUMENT" not in rows[0]:
            raise BadFile("old-format file without its columns")
        out = []
        for r in rows:
            if not (r.get("INSTRUMENT") or "").strip():
                continue
            kind, symbol, option = r["INSTRUMENT"].strip(), r["SYMBOL"].strip(), r["OPTION_TYP"].strip()
            if kind not in LEGACY_INSTRUMENTS:
                raise BadFile(f"unknown instrument {kind!r}")
            is_future = option == LEGACY_NO_OPTION_TYPE
            close = index_closes.get(INDEX_NAMES.get(symbol, ""))
            record = dict.fromkeys(COLUMNS, "")
            record.update(
                TradDt=legacy_date(r["TIMESTAMP"]),
                BizDt=legacy_date(r["TIMESTAMP"]),
                Sgmt="FO",
                Src="NSE",
                FinInstrmTp=LEGACY_INSTRUMENTS[kind],
                TckrSymb=symbol,
                XpryDt=legacy_date(r["EXPIRY_DT"]),
                StrkPric="" if is_future else r["STRIKE_PR"].strip(),
                OptnTp="" if is_future else option,
                UndrlygPric="" if close is None else f"{close:.2f}",
                TtlTrfVal=f"{float(r['VAL_INLAKH']) * RUPEES_PER_LAKH:.2f}",
                **{new: r[old].strip() for new, old in LEGACY_FIELDS.items()},
            )
            out.append(record)
        return out


FORMATS: tuple[FoFileFormat, ...] = (UdiffFormat(), LegacyFormat())


def read_fo_file(filename: str, data: bytes, index_closes: dict[str, float] | None = None) -> list[dict]:
    """All rows of one daily F&O file as records with the COLUMNS keys. `index_closes` (from read_index_closes for
    the same day) fills the underlying price of index options in old-format files."""
    for file_format in FORMATS:
        if file_format.recognises(filename):
            rows = list(csv.DictReader(io.StringIO(csv_text(filename, data))))
            if not rows:
                raise BadFile(f"{filename}: no rows")
            try:
                return file_format.records(rows, index_closes or {})
            except (KeyError, ValueError) as exc:
                raise BadFile(f"{filename}: {exc}") from exc
    raise BadFile(f"{filename}: not a known NSE F&O file name")
