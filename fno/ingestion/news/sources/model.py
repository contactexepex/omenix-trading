"""The data of the news source rules (NP1): plain frozen values, no behaviour. `SourceRules` answers the questions."""

from __future__ import annotations

from dataclasses import dataclass

PRIMARY, TIER_1, TIER_2, UNLISTED = "primary", "tier1", "tier2", "unlisted"
LISTED_TIERS = (PRIMARY, TIER_1, TIER_2)
TIERS = (*LISTED_TIERS, UNLISTED)

JSONLD, TRAFILATURA = "jsonld", "trafilatura"
EXTRACTORS = (JSONLD, TRAFILATURA)  # newspaper4k is deliberately not here (NP0 section 2e)


@dataclass(frozen=True)
class Outlet:
    """One allowlisted domain. `fetch=False`: the outlet refuses bot traffic, so its pages are never requested; its
    headline still gets its tier. `same_as`: another listed domain of the same outlet (one outlet, two hosts)."""

    domain: str
    tier: str
    names: tuple[str, ...] = ()
    fetch: bool = True
    https_links: bool = False
    extract: tuple[str, ...] = ()
    opinion_unless_path: str = ""
    same_as: str = ""
    note: str = ""


@dataclass(frozen=True)
class Wire:
    """A news agency: an item that names it is a copy of its story, one origin however many outlets carry it."""

    name: str
    names: tuple[str, ...] = ()
    attribution: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()


@dataclass(frozen=True)
class Promotional:
    """Vendor or promotional content: never an independent origin."""

    providers: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    text: tuple[str, ...] = ()
