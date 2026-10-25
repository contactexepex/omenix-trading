"""Composition root of the A16h feed probe (story A16h): the full Groww client is built here and wrapped at once,
the feed in `ReadOnlyFeed`, the REST client in A16's `ReadOnlyGroww` (one index quote per index for ATM); the
instrument tokens come from Groww's public instrument list (the SDK's own `INSTRUMENT_CSV_URL`). Nothing else holds
`GrowwFeed` or `GrowwAPI`."""

from __future__ import annotations

import csv
import io
import json
import os
import tempfile
import threading
import time as clock_module
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from types import SimpleNamespace

from ..config import ROOT
from ..models import now_ist
from ..providers import get_provider
from .feed_gate import alongside_gate, catch_up_gate
from .feed_probe import FeedProbe
from .feed_universe import INDICES, universe
from .index_reading import quote_reading
from .ledger import SlotLedger
from .read_only import ReadOnlyGroww
from .read_only_feed import ReadOnlyFeed
from .wiring import INTRADAY_FOLDER

INSTRUMENTS_TIMEOUT_SECONDS = 60
FEED_CONNECT_SECONDS = 30  # the SDK retries a failed connect for about 2 minutes on its own (23 Oct): end it sooner
NOT_CONNECTED = "the feed did not connect within {seconds:.0f} s"


class FeedNotConnected(RuntimeError):
    """The feed did not open in time (or its connect raised): the probe stops with one plain line."""


RUN_LOGS = ROOT / "journal" / "runs"  # O1's daily run log, one file per day


def build_feed_probe(cfg: dict, env: Mapping[str, str] = os.environ) -> tuple[FeedProbe, ReadOnlyGroww]:
    from growwapi import GrowwFeed
    from growwapi.groww import nats_client

    ca_file = feed_ca_file(env, Path(tempfile.mkdtemp(prefix="feed-ca-")))
    if ca_file:
        trust_for_feed(nats_client, ca_file)
    provider = get_provider("groww", cfg)  # GW1: its REST client keeps out of A16's marks
    feed = ReadOnlyFeed(open_feed(lambda: GrowwFeed(provider.feed_client()), FEED_CONNECT_SECONDS))
    return FeedProbe(feed, now_ist, clock_module.sleep), provider.api


def feed_ca_file(env: Mapping[str, str], folder: Path) -> str | None:
    """certifi's public roots **plus** the bundle in SSL_CERT_FILE (a TLS-re-terminating proxy's CA, 23 Oct) in one
    file; None when SSL_CERT_FILE is unset or missing. Added, never replacing: a host without the proxy still verifies,
    and verification stays on (orchestrator, 23 Oct)."""
    import certifi

    extra = env.get("SSL_CERT_FILE")
    if not extra or not Path(extra).is_file():
        return None
    combined = Path(folder) / "feed-ca.pem"
    combined.write_bytes(Path(certifi.where()).read_bytes() + b"\n" + Path(extra).read_bytes())
    return str(combined)


def trust_for_feed(nats_module, ca_file: str) -> None:
    """The SDK's feed builds its TLS context from `certifi.where()` alone (growwapi/groww/nats_client.py): it is given
    the combined file instead, in that one module only."""
    nats_module.certifi = SimpleNamespace(where=lambda: ca_file)


def open_feed(make: Callable[[], object], seconds: float) -> object:
    """Builds the feed in a thread joined for at most `seconds`; a slower or failed connect raises FeedNotConnected."""
    made: list[object] = []
    failed: list[BaseException] = []

    def build() -> None:
        try:
            made.append(make())
        except Exception as error:  # named by class only by the caller
            failed.append(error)

    worker = threading.Thread(target=build, daemon=True)  # a stuck SDK retry loop is left behind, never waited for
    worker.start()
    worker.join(seconds)
    if worker.is_alive():
        raise FeedNotConnected(NOT_CONNECTED.format(seconds=seconds))
    if failed:
        raise FeedNotConnected(f"the feed did not connect: {type(failed[0]).__name__}")
    return made[0]


def build_universe(client: ReadOnlyGroww, side: int, every_expiry: bool = False):
    from growwapi import GrowwAPI

    with urllib.request.urlopen(GrowwAPI.INSTRUMENT_CSV_URL, timeout=INSTRUMENTS_TIMEOUT_SECONDS) as answer:
        rows = list(csv.DictReader(io.StringIO(answer.read().decode("utf-8"))))
    spots = {}
    for name in INDICES:
        quote = client.get_quote(trading_symbol=name, exchange=client.EXCHANGE_NSE, segment=client.SEGMENT_CASH)
        level, _ = quote_reading(quote)
        if level:
            spots[name] = float(level)
    return universe(rows, spots, now_ist().date(), side, every_expiry)


def build_gate():
    ledger = SlotLedger(INTRADAY_FOLDER)
    return lambda day: alongside_gate(ledger.rows, day)


def build_catch_up_gate():
    """Reads the checkout's run log: pull `main` first (the routine commits it)."""

    def gate(day):
        path = RUN_LOGS / f"{day.isoformat()}.json"
        return catch_up_gate(json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None, day)

    return gate
