"""Where a story came from (NP5b; NP0 section 2f): `OriginReader` says whether an article is a copy of a news agency's
story. Pure, computed on read, from facts only: the outlet's host, the read file's provider and bylines, and the
title. The agencies, their names and their domains are the PUBLIC rules in `config/news_sources.yaml` (`SourceRules`).
An article whose host is an agency's own domain, whose JSON-LD provider or byline is the agency, or whose title ends
with an attribution to it ("... (AgencyA)", "... - AgencyA") is the agency's story: one origin however many outlets
carry it. Not used, by decision: a dateline in the first sentences of the text (no key sentences are stored, E1
default), so some agency copies are missed; the rate is unmeasured until real reads exist."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from fno.ingestion.news.sources.rules import SourceRules

DOMAIN, PROVIDER, BYLINE, TITLE = "domain", "provider", "byline", "title"
_BRACKETED_END = re.compile(r"[(\[]([^()\[\]]{1,40})[)\]]\s*$")
_DASHED_END = re.compile(r"\s[-–—|]\s+([^-–—|]{1,40})$")
_MAX_TITLE = 1_000


@dataclass(frozen=True)
class Origin:
    wire: str = ""  # the agency's name ("" when the article is not an agency copy)
    via: str = ""  # which fact said so: domain, provider, byline or title


class OriginReader:
    def __init__(self, rules: SourceRules):
        self.rules = rules

    def read(self, host: str | None, provider: str | None, authors: Iterable[str], title: str | None) -> Origin:
        """`host`: the effective outlet host; `provider`, `authors`: from the read file (empty without one)."""
        wire = self.rules.wire_of_domain(host)
        if wire:
            return Origin(wire, DOMAIN)
        wire = self.rules.wire_of_name(provider)
        if wire:
            return Origin(wire, PROVIDER)
        for author in authors:
            wire = self.rules.wire_of_name(author)
            if wire:
                return Origin(wire, BYLINE)
        for label in attributions(title or ""):
            wire = self.rules.wire_of_name(label)
            if wire:
                return Origin(wire, TITLE)
        return Origin()


def attributions(title: str) -> list[str]:
    """The labels a title ends with: the last bracketed one and the last one after a dash or bar."""
    text = title[:_MAX_TITLE].rstrip()
    return [m.group(1).strip() for m in (_BRACKETED_END.search(text), _DASHED_END.search(text)) if m]
