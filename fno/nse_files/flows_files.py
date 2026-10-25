"""Readers of the big investors' daily flows (story P8): NSE's provisional FII/FPI and DII cash-market values and
NSDL's daily FPI report. Both serve only their latest day, so the archive keeps one copy per day fetched; a reader
returns the session each copy covers, read from the copy itself."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import date, datetime

from ..fo_bhavcopy import BadFile

NSE_DATE, NSDL_DATE = "%d-%b-%Y", "%d-%b-%Y"
NSE_FII, NSE_DII = "FII/FPI", "DII"
NSDL_HEADING = re.compile(r"Daily Trends in FPI Investments on (\d{2}-[A-Za-z]{3}-\d{4})")
NSDL_EQUITY = re.compile(r"Equity Stock Exchange .*? Sub-total ([\d,.()-]+) ([\d,.()-]+) ([\d,.()-]+)")
TAGS, SPACES = re.compile(r"<[^>]+>"), re.compile(r"\s+")


@dataclass(frozen=True)
class FlowSide:
    buy: float  # Rs crore
    sell: float
    net: float


@dataclass(frozen=True)
class CashFlows:
    day: date
    fii: FlowSide
    dii: FlowSide


def read_fii_dii(data: bytes, filename: str) -> CashFlows:
    """The session and both sides of NSE's FII/DII file (provisional values, Rs crore)."""
    try:
        rows = {r["category"].strip(): r for r in json.loads(data.decode("utf-8"))}
        days = {datetime.strptime(r["date"], NSE_DATE).date() for r in rows.values()}
        if len(days) != 1 or {NSE_FII, NSE_DII} - set(rows):
            raise ValueError(f"needs one session with {NSE_FII} and {NSE_DII}")
        return CashFlows(days.pop(), _side(rows[NSE_FII]), _side(rows[NSE_DII]))
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise BadFile(f"{filename}: not NSE's FII/DII cash file ({exc})") from exc


def _side(row: dict) -> FlowSide:
    return FlowSide(float(row["buyValue"]), float(row["sellValue"]), float(row["netValue"]))


def read_nsdl_equity(data: bytes, filename: str) -> tuple[date, float]:
    """(reporting day, FPI equity net over all routes, Rs crore) from NSDL's latest daily report."""
    text = SPACES.sub(" ", html.unescape(TAGS.sub(" ", data.decode("utf-8", errors="replace"))))
    heading, equity = NSDL_HEADING.search(text), NSDL_EQUITY.search(text)
    if not heading or not equity:
        raise BadFile(f"{filename}: not NSDL's daily FPI report (no equity sub-total)")
    return datetime.strptime(heading.group(1), NSDL_DATE).date(), _crore(equity.group(3))


def _crore(text: str) -> float:
    """NSDL writes a negative amount in brackets: (198.82)."""
    clean = text.replace(",", "")
    return -float(clean.strip("()")) if clean.startswith("(") else float(clean)
