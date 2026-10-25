"""Readers of the NSE files the market read models are built from (story P6). Each returns plain records and raises
BadFile (a ValueError) for a file that is damaged or not in its layout, so the same functions check archived files."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

from ..fo_bhavcopy import BadFile, csv_text

EQUITY_SERIES = ("EQ", "BE")  # equity shares (rolling and trade-for-trade): the screener's stocks
NO_FIGURE = ("", "-")  # NSE writes "-" where it has no figure
EQUITY_COLUMNS = ("TradDt", "TckrSymb", "SctySrs", "ClsPric", "HghPric", "LwPric", "TtlTradgVol", "OpnPric")


@dataclass(frozen=True)
class EquityBar:
    day: date
    symbol: str
    series: str
    close: float
    high: float
    low: float
    volume: int
    open: float | None = None  # a demerger's ex-date open is NSE's discovered price (corporate_actions.py)


def read_equity_bhavcopy(data: bytes, filename: str) -> list[EquityBar]:
    """Every EQ and BE row of NSE's daily capital-market file (UDiFF)."""
    rows = list(csv.DictReader(io.StringIO(csv_text(filename, data))))
    if not rows or any(column not in rows[0] for column in EQUITY_COLUMNS):
        raise BadFile(f"{filename}: not NSE's capital-market file (needs {', '.join(EQUITY_COLUMNS)})")
    try:
        return [
            EquityBar(
                date.fromisoformat(r["TradDt"]),
                r["TckrSymb"],
                r["SctySrs"],
                float(r["ClsPric"]),
                float(r["HghPric"]),
                float(r["LwPric"]),
                int(float(r["TtlTradgVol"])),
                number(r["OpnPric"]),
            )  # fmt: skip
            for r in rows
            if r["SctySrs"] in EQUITY_SERIES
        ]
    except ValueError as exc:
        raise BadFile(f"{filename}: {exc}") from exc


def read_delivery(data: bytes, filename: str) -> dict[str, float | None]:
    """Symbol -> delivery % of the day, for EQ and BE rows (None where NSE gives no figure)."""
    text = data.decode("utf-8-sig").replace(", ", ",")  # NSE pads every value with a space
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or any(column not in rows[0] for column in ("SYMBOL", "SERIES", "DELIV_PER")):
        raise BadFile(f"{filename}: not NSE's security-wise delivery file")
    return {r["SYMBOL"]: number(r["DELIV_PER"]) for r in rows if r["SERIES"].strip() in EQUITY_SERIES}


def read_equity_list(data: bytes, filename: str) -> dict[str, str]:
    """Symbol -> company name, from NSE's list of listed companies."""
    return _two_columns(data, filename, "SYMBOL", "NAME OF COMPANY")


def read_nifty500_list(data: bytes, filename: str) -> dict[str, str]:
    """Symbol -> industry, for the Nifty 500's members."""
    return _two_columns(data, filename, "Symbol", "Industry")


def _two_columns(data: bytes, filename: str, key: str, value: str) -> dict[str, str]:
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    if not rows or key not in rows[0] or value not in rows[0]:
        raise BadFile(f"{filename}: needs the columns {key!r} and {value!r}")
    return {r[key]: r[value] for r in rows}


def number(text: str | None) -> float | None:
    text = (text or "").strip()
    return None if text in NO_FIGURE else float(text)


@dataclass(frozen=True)
class IndexFigures:
    close: float
    pe: float | None
    pb: float | None
    dividend_yield: float | None


def read_index_figures(data: bytes, filename: str) -> dict[str, IndexFigures]:
    """Index name -> close, P/E, P/B and dividend yield, from NSE's daily index-close file."""
    rows = list(csv.DictReader(io.StringIO(csv_text(filename, data))))
    if not rows or "Index Name" not in rows[0] or "Closing Index Value" not in rows[0]:
        raise BadFile(f"{filename}: not NSE's index-close file")
    return {
        r["Index Name"]: IndexFigures(
            float(r["Closing Index Value"]), number(r.get("P/E")), number(r.get("P/B")), number(r.get("Div Yield"))
        )
        for r in rows
        if number(r["Closing Index Value"]) is not None
    }


def read_fo_rows(data: bytes, filename: str) -> list[dict[str, str]]:
    """The raw rows of NSE's daily F&O file in the current (UDiFF) format, as NSE writes them."""
    rows = list(csv.DictReader(io.StringIO(csv_text(filename, data))))
    if not rows or "FinInstrmTp" not in rows[0]:
        raise BadFile(f"{filename}: not NSE's UDiFF F&O file")
    return rows
