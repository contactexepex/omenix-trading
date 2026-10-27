"""Reading and checking a company-list file (NP3a): `{"format": 1, "companies": [...]}`. It is the owner's private
content, so a refusal is ONE fixed code and never names a symbol, a name or a line. What is refused:

- a symbol that is not an NSE-style symbol, or a repeated one; a name or alias that is empty once normalised;
- two companies claiming one normalised name or alias (a tag would be ambiguous);
- an exclusion that is not a regular expression or does not fit `EXCLUSION_GRAMMAR`: plain text, `(?:A|B)` alternatives
  of plain text (at most `MAX_GROUPS`), `x?` for an optional letter (at most `MAX_OPTIONALS` per pattern) and one
  `\\w*` word tail at the end.
  Nothing else (no `.`, `*`, `+`, `{n,m}`, class or look-around), so no owner pattern can run long on a crafted
  headline. A list of shapes to refuse cannot be complete (measured: two `.*` took 14 s on 5,000 characters; 23 groups
  `(a|a)` took 20 s on 100), so the grammar allows only what has no repeat to multiply. The tagger (NP5) still cuts the
  text each pattern sees to a fixed length, so the worst-case time stays bounded even if this grammar is ever widened;
- an unknown key, a kind other than stock or index, more entries or longer texts than the caps below."""

from __future__ import annotations

import json
import re

from fno.ingestion.news import codes
from fno.ingestion.news.companies.model import KINDS, STOCK, Company, CompanyList
from fno.ingestion.news.sources.labels import normalise_label

FORMAT = 1
MAX_COMPANIES = 2000
MAX_ALIASES, MAX_EXCLUSIONS = 20, 20
MAX_TEXT, MAX_PATTERN = 120, 120
SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9&-]{0,19}$")
MAX_OPTIONALS, MAX_GROUPS = 4, 2  # each `x?` doubles the ways to match, each group multiplies them by its alternatives
_LETTER = r"(?:[A-Za-z0-9 &'-]|\\\.)"  # a plain character, or an escaped full stop
_ATOM = _LETTER + r"\??"  # a letter, optionally absent (`Lifespaces?`)
_SEQUENCE = f"(?:{_ATOM})+"
_GROUP = rf"\(\?:{_SEQUENCE}(?:\|{_SEQUENCE})*\)"  # (?:Alpha|Beta): alternatives of plain text, no quantifier after it
EXCLUSION_GRAMMAR = re.compile(rf"(?:{_ATOM}|{_GROUP})+(?:\\w\*)?")  # and at most one word tail, last
COMPANY_KEYS = frozenset({"symbol", "name", "aliases", "exclusions", "targeted", "kind"})
TOP_KEYS = frozenset({"format", "companies"})


class CompanyListError(Exception):
    """The list cannot be used; `str(error)` is one of the fixed codes."""


def _invalid() -> CompanyListError:
    return CompanyListError(codes.COMPANY_LIST_INVALID)


def _texts(value: object, limit: int) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > limit or not all(isinstance(v, str) and v.strip() for v in value):
        raise _invalid()
    if any(len(v) > MAX_TEXT or not normalise_label(v) for v in value):
        raise _invalid()
    return tuple(value)


def _exclusions(value: object) -> tuple[str, ...]:
    patterns = _texts(value, MAX_EXCLUSIONS)
    for pattern in patterns:
        if (
            len(pattern) > MAX_PATTERN
            or not EXCLUSION_GRAMMAR.fullmatch(pattern)
            or pattern.count("?") > MAX_OPTIONALS
            or pattern.count("(?:") > MAX_GROUPS
        ):
            raise _invalid()
        try:
            re.compile(pattern)
        except re.error:
            raise _invalid() from None
    return patterns


def _company(entry: object) -> Company:
    if not isinstance(entry, dict) or set(entry) - COMPANY_KEYS or not {"symbol", "name"} <= set(entry):
        raise _invalid()
    symbol, name, kind, targeted = (
        entry["symbol"],
        entry["name"],
        entry.get("kind", STOCK),
        entry.get("targeted", False),
    )
    if not isinstance(symbol, str) or not SYMBOL.match(symbol) or not isinstance(name, str) or len(name) > MAX_TEXT:
        raise _invalid()
    if not normalise_label(name) or kind not in KINDS or not isinstance(targeted, bool):
        raise _invalid()
    return Company(
        symbol, name, _texts(entry.get("aliases"), MAX_ALIASES), _exclusions(entry.get("exclusions")), targeted, kind
    )


def parse_company_list(data: bytes, version: int) -> CompanyList:
    try:
        document = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        raise _invalid() from None
    if not isinstance(document, dict) or set(document) != TOP_KEYS or document["format"] != FORMAT:
        raise _invalid()
    entries = document["companies"]
    if not isinstance(entries, list) or not 0 < len(entries) <= MAX_COMPANIES:
        raise _invalid()
    companies = tuple(_company(e) for e in entries)
    if len({c.symbol for c in companies}) != len(companies):
        raise _invalid()
    owner: dict[str, str] = {}
    for company in companies:
        for text in (company.name, *company.aliases):
            if owner.setdefault(normalise_label(text), company.symbol) != company.symbol:
                raise _invalid()
    return CompanyList(version, companies)
