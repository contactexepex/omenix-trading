"""The data of the news source rules (NP1): plain frozen values, no behaviour. `SourceRules` answers the questions.
Fields no code here reads (the tier, `https_links`, `opinion_unless_path`, wires, promotional) are the
schema of the public rules file, which the downstream consumer reads: kept on purpose, not dead code (DEL1, judges
117 and 118)."""

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


# Names under which anyone can publish: listing one would make every tenant "an allowlisted outlet" (`x.github.io`).
# A short curated list, NOT the full Public Suffix List (stated in NP1): the generic rule below covers the national
# second-level suffixes (`co.in`, `com.au`, `org.uk` ...), this set the common hosting platforms.
HOSTING_SUFFIXES = frozenset({
    "github.io", "gitlab.io", "pages.dev", "workers.dev", "vercel.app", "netlify.app", "herokuapp.com", "blogspot.com",
    "wordpress.com", "web.app", "firebaseapp.com", "azurewebsites.net", "appspot.com", "cloudfront.net",
    "s3.amazonaws.com",
})  # fmt: skip
SECOND_LEVEL_LABELS = frozenset({"co", "com", "org", "net", "gov", "ac", "edu", "or", "ne", "go", "nic", "res"})


def is_public_suffix(domain: str) -> bool:
    """True for a name no one organisation owns: a hosting platform, or a two-label `co.in`-style national suffix."""
    labels = domain.split(".")
    return domain in HOSTING_SUFFIXES or (len(labels) == 2 and labels[0] in SECOND_LEVEL_LABELS and len(labels[1]) == 2)
