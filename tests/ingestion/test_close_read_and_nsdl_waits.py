"""Story R1d3: the close read's three tries and the NSDL back-fill's 10 s gap on the shared resilience primitives, with
today's numbers: a live window (no jitter, no total limit, every failure retried) and one polite form post at a time (no
cap on how long a post waits for its turn). Offline, no real sleep."""

from __future__ import annotations

from datetime import date

import pytest

from fno.ingestion.close_read import reader as close_reader
from fno.ingestion.close_read.answer import Refused
from fno.ingestion.close_read.constants import TRIES, TRY_GAP_SECONDS
from fno.ingestion.flow_history.nsdl_backfill import GAP_SECONDS, NsdlBackfill


class Answers:
    def __init__(self, *steps):
        self.steps, self.calls = list(steps), 0

    def answer(self):
        self.calls += 1
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def _reader(steps, monkeypatch):
    waits = []
    monkeypatch.setattr(close_reader, "read_answer", lambda payload, day: f"read:{payload}")
    return close_reader.CloseReader(Answers(*steps), None, None, None, lambda: None, waits.append), waits


def test_the_close_read_policy_is_a_live_window_policy():
    settings = close_reader.READ_RETRY
    assert settings.waits == (60.0, 60.0) and settings.jitter == 0.0
    assert settings.max_total_seconds == float("inf") and settings.retry_after_ceiling_seconds == float("inf")
    assert (TRIES, TRY_GAP_SECONDS) == (3, 60)


def test_three_failing_tries_wait_exactly_120_seconds_in_all(monkeypatch):
    r, waits = _reader([Refused("no")] * 3, monkeypatch)
    r._read(date(2026, 10, 27))
    assert sum(waits) == 120.0 and r.source.calls == 3  # the 15:40 read budgets exactly this


def test_a_refusal_and_an_unexpected_error_are_both_retried_and_the_last_one_is_reported(monkeypatch):
    r, waits = _reader([Refused("early"), RuntimeError("https://secret"), Refused("still early")], monkeypatch)
    got, raw, reason = r._read(date(2026, 10, 27))
    assert (got, raw, reason) == (None, b"", "still early") and waits == [60, 60]


def test_the_nsdl_gap_has_no_budget_and_no_cap_on_the_wait():
    clock = []
    b = NsdlBackfill(None, None, None, None, lambda d: d, lambda s: clock.append(s), lambda: 0.0)
    for _ in range(40):  # a frozen clock: the 40th start is 390 s ahead, far past the library's default 120 s cap
        b._gap.acquire()
    settings = b._gap.settings
    assert (settings.per_minute, settings.per_day) == (None, None) and settings.max_wait_seconds == float("inf")
    assert settings.min_spacing_seconds == GAP_SECONDS == 10.0
    assert clock[-1] == pytest.approx(390.0)
