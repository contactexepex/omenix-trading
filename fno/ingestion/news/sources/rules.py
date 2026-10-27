"""Questions about the news source rules (NP1): what an outlet is, its tier, whether its pages may ever be requested,
who owns a label. Pure: no request, no clock, no file. Built by `loader.build_source_rules`.

A host matches a listed domain only at a dot boundary and only from the right (`m.economictimes.com` finds
`economictimes.com`; `reuters.com.evil.example`, `notreuters.com` and `evil-reuters.com` find nothing). A host that
is not a plain lower-case ASCII name (an address, a port, credentials, a space, non-ASCII) finds nothing: always
"unlisted"."""

from __future__ import annotations

import re

from fno.ingestion.news.sources.labels import normalise_label
from fno.ingestion.news.sources.model import UNLISTED, Outlet, Promotional, Wire

HOST_PREFIXES = ("www.", "m.", "amp.", "mobile.")  # the same outlet under another face
PLAIN_HOST = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
LABEL_IS_A_HOST = re.compile(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def plain_host(host: str | None) -> str:
    """The host in lower case without a trailing dot, or "" when it is not a plain ASCII host name. Whitespace anywhere,
    and any non-ASCII letter (also one that lower-casing would turn into ASCII, such as the Kelvin sign), make it ""."""
    text = host or ""
    if not text.isascii():
        return ""
    cleaned = text.lower().rstrip(".")
    return cleaned if PLAIN_HOST.match(cleaned) else ""


def _under(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


class SourceRules:
    def __init__(self, outlets: dict[str, Outlet], wires: tuple[Wire, ...], promotional: Promotional):
        self.outlets, self.wires, self.promotional = dict(outlets), wires, promotional
        self._label_domain = {normalise_label(n): o.domain for o in outlets.values() for n in o.names}
        self._wire_name = {normalise_label(n): w.name for w in wires for n in (w.name, *w.names)}
        self._promo_providers = {normalise_label(n) for n in promotional.providers}

    # outlets
    def lookup(self, host: str | None) -> Outlet | None:
        """The allowlisted outlet for a host or one of its parent domains, or None (unlisted)."""
        name = plain_host(host)
        parts = name.split(".")
        for start in range(max(len(parts) - 1, 0)):
            outlet = self.outlets.get(".".join(parts[start:]))
            if outlet is not None:
                return outlet
        return None

    def tier_of(self, host: str | None) -> str:
        outlet = self.lookup(host)
        return outlet.tier if outlet else UNLISTED

    def outlet_key(self, host: str | None) -> str:
        """One key per outlet: the listed domain (its `same_as` main domain when it has one), else the host without
        `www.`/`m.`/`amp.`/`mobile.`; "" for something that is not a host."""
        outlet = self.lookup(host)
        if outlet:
            return outlet.same_as or outlet.domain
        name = plain_host(host)
        while stripped := next((name.removeprefix(p) for p in HOST_PREFIXES if name.startswith(p)), None):
            name = stripped
        return name

    def may_fetch(self, host: str | None) -> bool:
        """True only for a listed outlet that does not refuse automated traffic. An unlisted host is never requested."""
        outlet = self.lookup(host)
        if outlet is None or not outlet.fetch:
            return False
        main = self.outlets.get(outlet.same_as) if outlet.same_as else None
        return main is None or main.fetch  # an alias never bypasses the main domain's fetch: false

    def may_upgrade_to_https(self, host: str | None) -> bool:
        """True when a feed's http:// link on this host may be stored as https:// (its pages are served over HTTPS)."""
        outlet = self.lookup(host)
        return bool(outlet and outlet.https_links)

    def is_opinion(self, host: str | None, path: str | None) -> bool:
        """An outlet that marks its news desk by a path prefix treats everything else, and an item with no known path,
        as opinion (never an independent origin)."""
        outlet = self.lookup(host)
        if not outlet or not outlet.opinion_unless_path:
            return False
        return not (path or "").startswith(outlet.opinion_unless_path)

    def domain_of_label(self, label: str | None) -> str | None:
        """The listed domain a source label names ('Business Today'), or a label that is itself a listed host."""
        key = normalise_label(label)
        domain = self._label_domain.get(key) if key else None  # an empty label names nothing
        if domain is None and label and LABEL_IS_A_HOST.match(label.strip()):
            outlet = self.lookup(label.strip())
            domain = outlet.domain if outlet else None
        return domain

    # wires and promotional content
    def wire_of_name(self, name: str | None) -> str | None:
        key = normalise_label(name)
        return self._wire_name.get(key) if key else None

    def wire_of_domain(self, host: str | None) -> str | None:
        name = plain_host(host)
        return next((w.name for w in self.wires if any(_under(name, d) for d in w.domains)), None) if name else None

    def is_promotional_provider(self, name: str | None) -> bool:
        key = normalise_label(name)
        return bool(key) and key in self._promo_providers

    def is_promotional_domain(self, host: str | None) -> bool:
        name = plain_host(host)
        return bool(name) and any(_under(name, d) for d in self.promotional.domains)
