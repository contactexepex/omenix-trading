"""Story R1d1: Groww's spacing and 429 pause on the shared resilience primitives, with TODAY's spacing and TODAY's pause
topology (one 60 s pause per GrowwProvider; the index recorders share their provider's). No host ceiling, no probe, no
half-open. No network, no real sleep: a fake `growwapi` module stands in for the SDK."""

from __future__ import annotations

import ast
import sys
import threading
import types
from pathlib import Path

import pytest

from fno.ingestion.intraday.candle_source import MIN_GAP_SECONDS, GrowwCandleSource
from fno.ingestion.intraday.groww_source import PER_SECOND
from fno.ingestion.intraday.pacing import RatePacer
from fno.ingestion.providers.groww import GrowwProvider
from fno.ingestion.providers.groww_rate_guard import GrowwRateLimited, GrowwRateLimitPaused
from fno.ingestion.quotes.indices import INDEX_PER_SECOND, INDEX_WORKERS
from fno.ingestion.quotes.slot import NIFTY_SLOT
from fno.shared.resilience.pause import FixedPause

FNO = Path(__file__).resolve().parents[2] / "fno"


class Clock:
    def __init__(self):
        self.now, self.slept = 0.0, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


# ---- the pause: fixed length, no probe ---------------------------------------------------------------------------


def test_a_fixed_pause_runs_its_length_and_ends_exactly_then():
    clock = Clock()
    pause = FixedPause(60, clock)
    assert pause.remaining() <= 0
    pause.start()
    clock.now = 59
    assert pause.remaining() == 1
    clock.now = 60
    assert pause.remaining() <= 0


def test_a_new_start_extends_the_pause_from_now():
    clock = Clock()
    pause = FixedPause(60, clock)
    pause.start()
    clock.now = 30
    pause.start()
    assert pause.remaining() == 60


# ---- the topology: one pause per provider --------------------------------------------------------------------------


class Code429(Exception):
    code = "429"


class FakeApi:
    EXCHANGE_NSE = "NSE"

    def __init__(self, token):
        self.refuse, self.calls = False, 0

    def get_quote(self, **kwargs):
        self.calls += 1
        if self.refuse:
            raise Code429("raw text")
        return {"ltp": 1}


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setitem(sys.modules, "growwapi", types.SimpleNamespace(GrowwAPI=FakeApi))
    monkeypatch.setattr(GrowwProvider, "_token", lambda self: "t")
    return lambda: GrowwProvider({})


def refuse_on(p, value):
    p._sign_in.client().refuse = value


def test_two_callers_of_one_provider_share_its_pause(provider):
    p = provider()
    refuse_on(p, True)
    with pytest.raises(GrowwRateLimited):
        p.api.get_quote()
    with pytest.raises(GrowwRateLimitPaused):  # a second caller of the same provider (the index recorders' case)
        p.api.get_quote()
    assert p._sign_in.client().calls == 1  # nothing reached Groww during the pause


def test_a_429_in_one_provider_does_not_pause_another_provider(provider):
    first, second = provider(), provider()
    refuse_on(first, True)
    with pytest.raises(GrowwRateLimited):
        first.api.get_quote()
    assert second.api.get_quote() == {"ltp": 1}


def test_when_the_pause_ends_every_waiting_reader_goes_at_once_with_no_probe(monkeypatch):
    from fno.ingestion.providers.groww_rate_guard import RateGuardedGroww, RateLimitPause

    clock, started = Clock(), threading.Barrier(5)
    api = FakeApi("t")
    guarded = RateGuardedGroww(lambda: api, RateLimitPause(clock=clock))
    api.refuse = True
    with pytest.raises(GrowwRateLimited):
        guarded.get_quote()
    api.refuse, clock.now, results = False, 60.0, []

    def read():
        started.wait(timeout=10)
        results.append(guarded.get_quote())

    threads = [threading.Thread(target=read, daemon=True) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert results == [{"ltp": 1}] * 5  # none deferred behind a single probe


# ---- the spacing: each caller's own, as today ----------------------------------------------------------------------


def test_each_callers_spacing_is_what_it_was():
    assert PER_SECOND == 4 and RatePacer(PER_SECOND).interval == 0.25
    assert INDEX_PER_SECOND == 2.5 and INDEX_WORKERS == 3 and RatePacer(INDEX_PER_SECOND).interval == 0.4
    assert MIN_GAP_SECONDS == 0.5
    assert NIFTY_SLOT.per_second is None  # the main NIFTY recorder is unpaced: no limiter, as today


def test_three_index_workers_share_one_pacer_so_the_combined_rate_is_2_5_a_second():
    clock = Clock()
    pacer = RatePacer(INDEX_PER_SECOND, clock, clock.sleep)
    for _ in range(11):  # any worker takes the next slot
        pacer.wait()
    assert clock.now == pytest.approx(10 * 0.4)  # 11 starts in 4 s: 2.5 a second, the first free


def test_the_candle_source_starts_calls_half_a_second_apart():
    clock = Clock()
    api = types.SimpleNamespace(
        EXCHANGE_NSE="NSE", SEGMENT_CASH="C", CANDLE_INTERVAL_MIN_15="15", CANDLE_INTERVAL_MIN_1="1",
        get_historical_candles=lambda **kw: {"candles": []},
    )  # fmt: skip
    source = GrowwCandleSource(api, lambda: __import__("datetime").datetime(2026, 10, 27, 16, 0), clock.sleep, clock)
    from datetime import date

    for _ in range(3):
        source.candles(date(2026, 10, 26), date(2026, 10, 26))
    assert clock.slept == [0.5, 0.5]


# ---- every Groww composition root builds one provider (found by scanning, not by a list) ----------------------------


def _calls_in(path: Path, names: set[str]) -> list[int]:
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name in names:
                found.append(node.lineno)
    return found


def test_every_place_that_builds_a_groww_provider_is_known_and_builds_one():
    sites = {
        f"{p.relative_to(FNO).as_posix()}:{n}"
        for p in FNO.rglob("*.py")
        for n in _calls_in(p, {"GrowwProvider", "get_provider"})
    }
    assert {s.rsplit(":", 1)[0] for s in sites} == {
        "ingestion/cli.py",
        "ingestion/providers/__init__.py",
        "ingestion/providers/groww_check.py",
        "ingestion/intraday/wiring.py",
        "ingestion/intraday/feed_wiring.py",
        "ingestion/intraday/backfill_wiring.py",
        "ingestion/quotes/index_wiring.py",
        "ingestion/quotes/window_wiring.py",
        "ingestion/composition.py",
        "ingestion/preopen/wiring.py",
    }  # a new site must be added here on purpose, with the one-provider-per-process reasoning
    for path in {s.rsplit(":", 1)[0] for s in sites}:
        assert len(_calls_in(FNO / path, {"GrowwProvider", "get_provider"})) <= 1 or path.endswith(
            "providers/__init__.py"
        )
