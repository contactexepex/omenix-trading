"""Which addresses a page request may reach (NP4a, judge 84 F2). A listed outlet name is public and trusted, but a name
can resolve anywhere, so before every connection (every redirect hop included) EVERY address it resolves to, IPv4 and
IPv6, must be a global address. Python's `is_private` alone misses carrier-grade NAT (`100.64.0.0/10`: private False,
reserved False, global False), so the test is `is_global`. Also refused: an IPv4-mapped IPv6 address whose IPv4 is not
global, and the NAT64 ranges (Python calls `64:ff9b::7f00:1` global, but it embeds an IPv4 address we cannot vouch
for)."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable

NAT64 = (ipaddress.ip_network("64:ff9b::/96"), ipaddress.ip_network("64:ff9b:1::/48"))

Resolver = Callable[[str], list[str]]


def system_resolver(host: str) -> list[str]:
    """Every address the system resolves the name to (IPv4 and IPv6); raises OSError when it does not resolve."""
    return sorted({info[4][0] for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})


def is_reachable(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return ip.ipv4_mapped.is_global
        if any(ip in network for network in NAT64):
            return False
    return ip.is_global and not ip.is_multicast  # Python calls some multicast ranges global


def all_global(host: str, resolver: Resolver = system_resolver) -> bool:
    """True only when the name resolves, and every address it resolves to is reachable."""
    try:
        addresses = resolver(host)
    except OSError:
        return False
    return bool(addresses) and all(is_reachable(a) for a in addresses)
