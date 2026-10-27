"""Reading and checking a company-list file (NP3a): `{"format": 1, "companies": [...]}`. It is the owner's private
content, so a refusal is ONE fixed code and never names a symbol, a name or a line. What is refused:

- a symbol that is not an NSE-style symbol, or a repeated one; a name or alias that is empty once normalised;
- two companies claiming one normalised name or alias (a tag would be ambiguous);
- an exclusion that is not a regular expression, is long, puts a quantifier after a group, or has more than
  `MAX_OPEN_REPEATS` open-ended repeats (`*`, `+`, `{n,}`) or `MAX_OPTIONALS` optional parts: each extra open repeat
  multiplies the work on a crafted headline (measured: six `.*` on 90 characters ran 18 s), each extra `?` doubles it;
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
QUANTIFIED_GROUP = re.compile(
    r"\)\s*(?:[*+{]|\?\?)"
)  # a group followed by * + {n,m} (`)?` is allowed: one optional group)
MAX_OPEN_REPEATS, MAX_OPTIONALS = 2, 4
CLASS_OR_ESCAPE = re.compile(r"\[(?:\\.|[^\]\\])*\]|\\.")  # `[...]` and `\x` count as one plain character
OPEN_REPEAT = re.compile(r"[*+]|\{\d*,\d*\}")
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


def _too_costly(pattern: str) -> bool:
    plain = CLASS_OR_ESCAPE.sub("x", pattern).replace("(?", "(")  # a group's own `(?` is not a repeat
    plain = re.sub(r"([*+?}])\?", r"\1", plain)  # a lazy mark is not a second repeat
    return len(OPEN_REPEAT.findall(plain)) > MAX_OPEN_REPEATS or plain.count("?") > MAX_OPTIONALS


def _exclusions(value: object) -> tuple[str, ...]:
    patterns = _texts(value, MAX_EXCLUSIONS)
    for pattern in patterns:
        if len(pattern) > MAX_PATTERN or QUANTIFIED_GROUP.search(pattern) or _too_costly(pattern):
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
