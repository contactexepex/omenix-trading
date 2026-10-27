"""What a cluster's articles say about how many places the story came from (NP6b; NP0 section 2i). Values only."""

from __future__ import annotations

from dataclasses import dataclass

LABEL_WIRE, LABEL_OUTLET = "wire:", "outlet:"
PROMOTIONAL_PROVIDER, SINGLE_SOURCE, NO_VETTED_ORIGIN = "promotional_provider", "single_source", "no_vetted_origin"
ORIGINS_UNVERIFIED, OPINION, LOW_TIER_ONLY, UNREAD = "origins_unverified", "opinion", "low_tier_only", "unread"


@dataclass(frozen=True)
class OriginGroup:
    label: str  # `wire:<agency>` or `outlet:<outlet key>`
    keys: tuple[str, ...]  # the articles of the group, sorted
    countable: bool  # at least one article is listed, not promotional and not opinion
    verified: bool  # a countable article whose page was read, or whose agency has evidence other than its title


@dataclass(frozen=True)
class Corroboration:
    groups: tuple[OriginGroup, ...]  # sorted by label
    independent_origins: int  # verified groups
    unverified_origins: int  # countable groups that are not verified
    flags: tuple[str, ...]
    reads_used: int  # articles of the cluster with a read file
    rules_version: str  # what the caller says the rule files were (the source rules have no number of their own)
