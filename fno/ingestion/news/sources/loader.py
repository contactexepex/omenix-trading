"""Reading `config/news_sources.yaml` into `SourceRules` (NP1). The file is public data reviewed by git, but a typo
must still be an error: an unknown key, a bad tier, a `same_as` that points nowhere, a name two outlets claim, an
extractor we do not run, or a pattern that is not a regular expression all stop the load with one sentence. Nothing
here makes a request."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from fno.ingestion.news.sources.labels import normalise_label
from fno.ingestion.news.sources.model import EXTRACTORS, LISTED_TIERS, Outlet, Promotional, Wire
from fno.ingestion.news.sources.rules import SourceRules
from fno.shared.config import ROOT

DEFAULT_PATH = ROOT / "config" / "news_sources.yaml"
TOP_KEYS = frozenset({"domains", "wires", "promotional"})
OUTLET_KEYS = frozenset({"tier", "names", "fetch", "https_links", "extract", "opinion_unless_path", "same_as", "note"})
WIRE_KEYS = frozenset({"names", "attribution", "domains"})
PROMOTIONAL_KEYS = frozenset({"providers", "domains", "text"})
DOMAIN = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


class SourceRulesError(ValueError):
    """The rules file cannot be used; the message says which entry and why (the file is public, so it may name it)."""


def load_source_rules(path: Path = DEFAULT_PATH) -> SourceRules:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError, UnicodeDecodeError):
        raise SourceRulesError("the news source rules file cannot be read as YAML") from None
    return build_source_rules(document)


def build_source_rules(document: object) -> SourceRules:
    if not isinstance(document, dict) or not document.get("domains"):
        raise SourceRulesError("the news source rules need a non-empty `domains` map")
    _only(document, TOP_KEYS, "top level")
    outlets = {_domain(d, "domains"): _outlet(d, s) for d, s in document["domains"].items()}
    _check_same_as(outlets)
    _check_labels(outlets)
    wires = tuple(_wire(n, s, outlets) for n, s in (document.get("wires") or {}).items())
    return SourceRules(outlets, wires, _promotional(document.get("promotional") or {}))


def _only(section: dict, allowed: frozenset[str], where: str) -> None:
    unknown = sorted(str(k) for k in section if k not in allowed)
    if unknown:
        raise SourceRulesError(f"unknown key(s) in {where}: {', '.join(unknown)}")


def _domain(value: object, where: str) -> str:
    if not isinstance(value, str) or not DOMAIN.match(value):
        raise SourceRulesError(f"{where}: {value!r} is not a lower-case host name")
    return value


def _strings(value: object, where: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise SourceRulesError(f"{where}: expected a list of non-empty strings")
    return tuple(value)


def _flag(settings: dict, key: str, default: bool, domain: str) -> bool:
    value = settings.get(key, default)
    if not isinstance(value, bool):
        raise SourceRulesError(f"{domain}: `{key}` must be true or false")
    return value


def _outlet(domain: str, settings: object) -> Outlet:
    if not isinstance(settings, dict):
        raise SourceRulesError(f"{domain}: settings must be a map")
    _only(settings, OUTLET_KEYS, domain)
    tier = settings.get("tier")
    if tier not in LISTED_TIERS:
        raise SourceRulesError(f"{domain}: tier must be one of {', '.join(LISTED_TIERS)}")
    extract = _strings(settings.get("extract"), f"{domain} extract")
    if any(name not in EXTRACTORS for name in extract):
        raise SourceRulesError(
            f"{domain}: extract names an extractor omenix does not run (allowed: {', '.join(EXTRACTORS)})"
        )
    return Outlet(
        domain=domain,
        tier=tier,
        names=_strings(settings.get("names"), f"{domain} names"),
        fetch=_flag(settings, "fetch", True, domain),
        https_links=_flag(settings, "https_links", False, domain),
        extract=extract,
        opinion_unless_path=_text(settings, "opinion_unless_path", domain),
        same_as=_text(settings, "same_as", domain),
        note=_text(settings, "note", domain),
    )  # fmt: skip


def _text(settings: dict, key: str, domain: str) -> str:
    value = settings.get(key, "")
    if not isinstance(value, str):
        raise SourceRulesError(f"{domain}: `{key}` must be text")
    return value


def _check_same_as(outlets: dict[str, Outlet]) -> None:
    for outlet in outlets.values():
        target = outlet.same_as
        if not target:
            continue
        if target == outlet.domain or target not in outlets:
            raise SourceRulesError(f"{outlet.domain}: same_as must name another listed domain")
        if outlets[target].same_as:
            raise SourceRulesError(
                f"{outlet.domain}: same_as must name a domain that is itself the main one (no chains)"
            )


def _check_labels(outlets: dict[str, Outlet]) -> None:
    owner: dict[str, str] = {}
    for outlet in outlets.values():
        for name in outlet.names:
            label = normalise_label(name)
            if owner.setdefault(label, outlet.domain) != outlet.domain:
                raise SourceRulesError(f"the name {name!r} is claimed by both {owner[label]} and {outlet.domain}")


def _wire(name: str, settings: object, outlets: dict[str, Outlet]) -> Wire:
    if not isinstance(name, str) or not isinstance(settings, dict):
        raise SourceRulesError("each wire needs a name and a map of settings")
    _only(settings, WIRE_KEYS, f"wire {name}")
    domains = tuple(
        _domain(d, f"wire {name} domains") for d in _strings(settings.get("domains"), f"wire {name} domains")
    )
    return Wire(name, _strings(settings.get("names"), f"wire {name} names"),
                _strings(settings.get("attribution"), f"wire {name} attribution"), domains)  # fmt: skip


def _promotional(section: object) -> Promotional:
    if not isinstance(section, dict):
        raise SourceRulesError("`promotional` must be a map")
    _only(section, PROMOTIONAL_KEYS, "promotional")
    domains = tuple(_domain(d, "promotional domains") for d in _strings(section.get("domains"), "promotional domains"))
    text = _strings(section.get("text"), "promotional text")
    for pattern in text:
        try:
            re.compile(pattern)
        except re.error:
            raise SourceRulesError(f"promotional text pattern {pattern!r} is not a regular expression") from None
    return Promotional(_strings(section.get("providers"), "promotional providers"), domains, text)
