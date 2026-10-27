"""The first company list (NP3a), built from NSE's own archived lists: the F&O underlyings (`fo_mktlots`: UNDERLYING,
SYMBOL), the Nifty 500 (Company Name, Symbol) and the equity list (SYMBOL, NAME OF COMPANY). Pure: bytes in, the
file's bytes out.

The F&O master's company names are abbreviated by NSE ("APOLLO HOSPITALS ENTER. L", "MOTILAL OSWAL FIN LTD", strong
evidence: I read a real file), so the name comes from the equity list when it has the symbol, then the Nifty 500 list,
and only last from the master. A name is then cleaned mechanically: legal suffixes dropped, spaces collapsed, upper
case turned to title case. That is a starting point the owner edits: aliases and exclusions are empty except for the
four index underlyings, whose public names are written below. Nobody's selection of companies is in this code: the
universe is whatever NSE's lists hold."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass

from fno.ingestion.news.companies.model import INDEX, STOCK
from fno.ingestion.news.companies.parse import FORMAT, MAX_TEXT, SYMBOL, parse_company_list
from fno.ingestion.news.sources.labels import normalise_label
from fno.ingestion.research_data.fo_masters import LOT_KEY_COLUMNS, LOT_SECTION_SYMBOL

INDEX_ALIASES = {  # public names of the index underlyings (NSE's own); the symbol is matched separately
    "NIFTY": ("Nifty 50", "Nifty"),
    "BANKNIFTY": ("Bank Nifty", "Nifty Bank"),
    "FINNIFTY": ("Fin Nifty", "Nifty Financial Services"),
    "MIDCPNIFTY": ("Midcap Nifty", "Nifty Midcap Select"),
}
LEGAL_SUFFIX = re.compile(r"[\s,.]+(?:limited|ltd|l)\.?$", re.IGNORECASE)


@dataclass(frozen=True)
class Seed:
    data: bytes
    stocks: int
    indices: int
    renamed: int  # names that collided and were given their full form
    skipped: int = 0  # NSE rows the list checks would refuse (odd symbol, empty or long name, name taken twice)


def clean_name(raw: str) -> str:
    name = re.sub(r"\s+", " ", raw.replace("’", "'")).strip()
    while (shorter := LEGAL_SUFFIX.sub("", name)) != name:
        name = shorter
    name = name.strip(" ,.")
    short_acronym = " " not in name and len(name) <= 5  # ITC, LTM, TCS stay as they are
    return name.title() if name.isupper() and not short_acronym else name


def _rows(data: bytes) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]


def _underlyings(lots: bytes) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(index rows, stock rows) of (symbol, UNDERLYING): the stock section opens with a repeated header row."""
    rows = [[c.strip() for c in row] for row in csv.reader(io.StringIO(lots.decode("utf-8-sig"))) if row]
    if not rows or tuple(rows[0][:2]) != LOT_KEY_COLUMNS:
        raise ValueError("not an F&O master")
    indices: list[tuple[str, str]] = []
    stocks: list[tuple[str, str]] = []
    section = indices
    for row in rows[1:]:
        if row[1] == LOT_SECTION_SYMBOL:
            section = stocks
        elif SYMBOL.match(row[1]):
            section.append((row[1], row[0]))
    return indices, stocks


def build_seed(lots: bytes, equity_list: bytes | None, nifty500: bytes | None) -> Seed:
    indices, fno_stocks = _underlyings(lots)
    legal = {r["SYMBOL"]: r["NAME OF COMPANY"] for r in _rows(equity_list)} if equity_list else {}
    n500 = {r["Symbol"]: r["Company Name"] for r in _rows(nifty500)} if nifty500 else {}
    master = dict(fno_stocks)
    symbols = sorted(set(master) | set(n500))
    entries, taken, renamed, skipped = [], set(), 0, 0
    for symbol in symbols:
        raw = legal.get(symbol) or n500.get(symbol) or master[symbol]
        name = clean_name(raw) or re.sub(r"\s+", " ", raw).strip()
        if normalise_label(name) in taken:  # two symbols with one cleaned name: the second keeps its full form
            name, renamed = re.sub(r"\s+", " ", raw).strip().title(), renamed + 1
        if not SYMBOL.match(symbol) or not normalise_label(name) or len(name) > MAX_TEXT:
            skipped += 1
            continue
        if normalise_label(name) in taken:  # even its full form is taken
            skipped += 1
            continue
        taken.add(normalise_label(name))
        entries.append({"symbol": symbol, "name": name, "kind": STOCK})
    stocks = len(entries)
    for symbol, underlying in indices:
        entries.append({"symbol": symbol, "name": clean_name(underlying), "kind": INDEX,
                        "aliases": list(INDEX_ALIASES.get(symbol, ()))})  # fmt: skip
    document = {"format": FORMAT, "companies": entries}
    data = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    parse_company_list(data, 1)  # what a consumer will apply: a file it would refuse is never handed back to be written
    return Seed(data, stocks, len(indices), renamed, skipped)
