"""Which addresses a page request may reach (NP4a, judge 84 F2). A listed outlet name is public and trusted, but a name
can resolve anywhere, so before every connection (every redirect hop included) EVERY address it resolves to, IPv4 and
IPv6, must be a global address. Python's `is_private` alone misses carrier-grade NAT (`100.64.0.0/10`: private False,
reserved False, global False), so the test is `is_global`. Also refused: an IPv4-mapped IPv6 address whose IPv4 is not
global, and the IPv6 ranges that Python calls global but that embed an IPv4 address or are not for public use: NAT64
(`64:ff9b::7f00:1`), IPv4-compatible (`::127.0.0.1`), site-local (`fec0::/10`) and ORCHIDv2 (`2001:20::/28`)."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable

# IPv6 ranges Python calls global that either embed an IPv4 address we cannot vouch for or are not for public use
REFUSED_V6 = tuple(ipaddress.ip_network(n) for n in (
    "64:ff9b::/96", "64:ff9b:1::/48",  # NAT64 (embeds an IPv4 address)
    "::/96",  # IPv4-compatible (deprecated; embeds an IPv4 address): ::127.0.0.1
    "fec0::/10",  # deprecated site-local
    "2001:20::/28",  # ORCHIDv2 (not routable)
))  # fmt: skip

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
        if any(ip in network for network in REFUSED_V6):
            return False
    return ip.is_global and not ip.is_multicast  # Python calls some multicast ranges global


def all_global(host: str, resolver: Resolver = system_resolver) -> bool:
    """True only when the name resolves, and every address it resolves to is reachable."""
    try:
        addresses = resolver(host)
    except OSError:
        return False
    return bool(addresses) and all(is_reachable(a) for a in addresses)
