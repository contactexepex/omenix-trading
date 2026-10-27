"""NP4a: which addresses a page request may reach (judge 84 F2)."""

from __future__ import annotations

import pytest

from fno.ingestion.news.pages.address import all_global, is_reachable


@pytest.mark.parametrize("address", ["8.8.8.8", "93.184.216.34", "2606:4700:4700::1111", "::ffff:8.8.8.8"])
def test_a_global_address_is_reachable(address):
    assert is_reachable(address)


@pytest.mark.parametrize(
    "address",
    [
        "10.0.0.1", "127.0.0.1", "169.254.169.254", "192.168.1.1", "172.16.0.1", "0.0.0.0", "224.0.0.1",
        "239.1.1.1", "ff0e::1",
        "100.64.0.1", "100.127.255.254",  # carrier-grade NAT: private False, reserved False, global False
        "198.18.0.1", "192.0.0.8", "::1", "fe80::1", "fc00::1", "::ffff:10.0.0.1", "::ffff:100.64.0.1",
        "::127.0.0.1", "::a00:1", "::8.8.8.8", "fec0::1", "2001:20::1", "2001:2f::1",
        "64:ff9b::7f00:1", "64:ff9b::808:808", "64:ff9b:1::1",  # NAT64: Python calls it global, it embeds an IPv4
        "not an address", "", "999.1.1.1",
    ],
)  # fmt: skip
def test_everything_else_is_refused(address):
    assert not is_reachable(address)


def test_a_name_is_reachable_only_when_every_address_it_resolves_to_is_global():
    assert all_global("a.example", lambda host: ["8.8.8.8", "2606:4700:4700::1111"])
    assert not all_global("a.example", lambda host: ["8.8.8.8", "100.64.0.1"])  # one bad address among good ones
    assert not all_global("a.example", lambda host: [])


def test_a_name_that_does_not_resolve_is_refused_not_raised():
    def broken(host):
        raise OSError("no such host")

    assert not all_global("a.example", broken)
