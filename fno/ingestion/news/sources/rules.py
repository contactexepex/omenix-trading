"""Questions about the news source rules (NP1): whether an outlet is listed and whether its pages may ever be requested
(DEL1 removed the tier, wire, promotional, opinion and label questions: this repository does not classify). Pure: no
request, no clock, no file. Built by `loader.build_source_rules`.

A host matches a listed domain only at a dot boundary and only from the right (`m.economictimes.com` finds
`economictimes.com`; `reuters.com.evil.example`, `notreuters.com` and `evil-reuters.com` find nothing). A host that
is not a plain lower-case ASCII name (an address, a port, credentials, a space, non-ASCII) finds nothing: always
"unlisted"."""

from __future__ import annotations

import re

from fno.ingestion.news.sources.model import Outlet, Promotional, Wire

PLAIN_HOST = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")


def plain_host(host: str | None) -> str:
    """The host in lower case without a trailing dot, or "" when it is not a plain ASCII host name. Whitespace anywhere,
    and any non-ASCII letter (also one that lower-casing would turn into ASCII, such as the Kelvin sign), make it ""."""
    text = host or ""
    if not text.isascii():
        return ""
    cleaned = text.lower().rstrip(".")
    return cleaned if PLAIN_HOST.fullmatch(cleaned) else ""


class SourceRules:
    def __init__(self, outlets: dict[str, Outlet], wires: tuple[Wire, ...], promotional: Promotional):
        self.outlets, self.wires, self.promotional = dict(outlets), wires, promotional

    # outlets
    def _listed_suffixes(self, host: str | None) -> list[Outlet]:
        """Every listed outlet the host is, or is a subdomain of, nearest first."""
        parts = plain_host(host).split(".")
        found = (self.outlets.get(".".join(parts[start:])) for start in range(max(len(parts) - 1, 0)))
        return [outlet for outlet in found if outlet is not None]

    def lookup(self, host: str | None) -> Outlet | None:
        """The allowlisted outlet for a host or one of its parent domains, or None (unlisted)."""
        listed = self._listed_suffixes(host)
        return listed[0] if listed else None

    def may_fetch(self, host: str | None) -> bool:
        """True only for a listed outlet that does not refuse automated traffic. An unlisted host is never requested.
        EVERY listed domain the host sits under must allow it: a separately listed child of a `fetch: false` outlet is
        not fetchable (judge 84 F1), and an alias never bypasses its main domain's `fetch: false`."""
        listed = self._listed_suffixes(host)
        return bool(listed) and all(self._allows_fetch(outlet) for outlet in listed)

    def _allows_fetch(self, outlet: Outlet) -> bool:
        main = self.outlets.get(outlet.same_as) if outlet.same_as else None
        return outlet.fetch and (main is None or main.fetch)
