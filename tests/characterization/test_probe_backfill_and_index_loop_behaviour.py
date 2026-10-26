"""Story R1d, step 0 (part 2): today's exact retry gaps in the filings probe, the NSDL back-fill and the index recording
loop, pinned before they move onto the shared resilience layer. Offline, no real sleep. The window waits themselves stay
as they are (R1 story); only the gaps are pinned. Passes on `main` unchanged."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from fno.ingestion.filings import cli as filings_cli
from fno.ingestion.flow_history import nsdl_backfill
from fno.ingestion.flow_history.nsdl import BadAnswer
from fno.ingestion.flow_history.nsdl_backfill import NsdlBackfill, NsdlUnavailable
from fno.ingestion.quotes import indices
from fno.ingestion.quotes.recorder import RETRY_GAP_SECONDS, RecordResult
from fno.shared.models import IST

# ---- the filings probe ------------------------------------------------------------------------------------------


class Index:
    name = "filings index"

    def __init__(self, *steps):
        self.steps, self.calls = list(steps), 0

    def filings(self, symbol, since):
        self.calls += 1
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def test_the_probe_tries_twice_with_a_thirty_second_pause_after_each_failure(capsys):
    assert (filings_cli.PROBE_ATTEMPTS, filings_cli.PROBE_PAUSE_SECONDS) == (2, 30)
    waits, index = [], Index(RuntimeError("down"), RuntimeError("down"))
    assert filings_cli._probe(index, date(2026, 1, 1), waits.append) is False
    assert waits == [30, 30] and index.calls == 2  # it also pauses after the last failure, as today
    out = capsys.readouterr().out
    assert "FAILED (try 1): RuntimeError" in out and "FAILED (try 2): RuntimeError" in out
    assert "down" not in out.replace("FAILED", "")  # the exception's text is never printed


def test_the_probe_stops_at_the_first_answer(capsys):
    waits, index = [], Index(RuntimeError("slow"), [1, 2, 3])
    assert filings_cli._probe(index, date(2026, 1, 1), waits.append) is True
    assert waits == [30] and "answers: 3 TCS filings in 3 years" in capsys.readouterr().out


# ---- the NSDL back-fill -----------------------------------------------------------------------------------------


class Form:
    def __init__(self, *steps):
        self.steps, self.calls, self.forgotten = list(steps), 0, 0

    def month(self, month_end):
        self.calls += 1
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    def forget(self):
        self.forgotten += 1


class Clock:
    def __init__(self):
        self.now, self.slept = 0.0, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def backfill(form, clock, monkeypatch, read=lambda page, day: page):
    monkeypatch.setattr(nsdl_backfill, "read_fpi_month", read)
    return NsdlBackfill(form, None, None, None, lambda d: d, clock.sleep, clock)


def test_nsdl_makes_two_tries_per_month_forgetting_the_form_between(monkeypatch):
    assert nsdl_backfill.TRIES_PER_MONTH == 2
    clock, form = Clock(), Form(NsdlUnavailable("HTTP 500"), NsdlUnavailable("HTTP 500"))
    b = backfill(form, clock, monkeypatch)
    with pytest.raises(NsdlUnavailable):
        b._fetch(date(2026, 9, 30))
    assert form.calls == 2 and form.forgotten == 2


def test_nsdl_recovers_on_the_retry(monkeypatch):
    clock, form = Clock(), Form(BadAnswer("garbled"), "page")
    b = backfill(form, clock, monkeypatch)
    assert b._fetch(date(2026, 9, 30)) == ("page", "page") and form.forgotten == 1


def test_nsdl_calls_start_at_least_gap_seconds_apart(monkeypatch):
    clock, form = Clock(), Form("a", "b", "c")
    b = backfill(form, clock, monkeypatch)
    for _ in range(3):
        b._fetch(date(2026, 9, 30))
    assert nsdl_backfill.GAP_SECONDS == 10.0 and clock.slept == [10.0, 10.0]


def test_nsdl_a_failed_month_is_listed_and_the_pass_goes_on(monkeypatch):
    clock = Clock()
    form = Form(NsdlUnavailable("HTTP 503"), NsdlUnavailable("HTTP 503"))
    b = backfill(form, clock, monkeypatch)
    b._done = lambda month_end: False
    result = b.run([date(2026, 9, 30)])
    assert result.failed == {date(2026, 9, 30): "HTTP 503"} and result.saved == [] and form.calls == 2


# ---- the index recording loop's retry gap -----------------------------------------------------------------------


class Recorder:
    def __init__(self, results):
        self.results, self.attempts, self.closed = list(results), 0, []

    def is_session(self, day):
        return True

    def canonical(self, day):
        return None

    def attempt_now(self):
        self.attempts += 1
        return self.results.pop(0)

    def close_day(self, day):
        self.closed.append(day)


def test_an_incomplete_index_is_retried_every_sixty_seconds_until_it_completes():
    assert RETRY_GAP_SECONDS == 60
    now = [datetime(2026, 10, 27, 15, 2, tzinfo=IST)]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] = now[0].replace(minute=now[0].minute + 1)

    incomplete = RecordResult(indices.ATTEMPTED)
    complete = RecordResult(indices.ATTEMPTED, complete=True)
    recorder = Recorder([incomplete, incomplete, complete])
    results = indices.IndexRecording({"BANKNIFTY": recorder}, lambda: now[0], sleep).run()
    assert sleeps == [60, 60] and recorder.attempts == 3 and results["BANKNIFTY"].complete
    assert recorder.closed == []


def test_an_index_still_incomplete_at_the_window_end_is_closed_none():
    now = [datetime(2026, 10, 27, 15, 11, tzinfo=IST)]

    def sleep(seconds):
        now[0] = now[0].replace(minute=now[0].minute + 1)

    recorder = Recorder([RecordResult(indices.ATTEMPTED)] * 10)
    indices.IndexRecording({"BANKNIFTY": recorder}, lambda: now[0], sleep).run()
    assert recorder.attempts == 3 and len(recorder.closed) == 1  # 15:11, 15:12, 15:13; the window ends at 15:13


def test_no_index_attempt_starts_after_the_window_end_even_mid_round():
    now = [datetime(2026, 10, 27, 15, 12, 30, tzinfo=IST)]

    class Slow(Recorder):
        def attempt_now(self):
            now[0] = now[0].replace(minute=13, second=30)  # this attempt runs past the 15:13 end
            return super().attempt_now()

    first, second = Slow([RecordResult(indices.ATTEMPTED)]), Recorder([RecordResult(indices.ATTEMPTED)])
    indices.IndexRecording({"BANKNIFTY": first, "FINNIFTY": second}, lambda: now[0], lambda s: None).run()
    assert first.attempts == 1 and second.attempts == 0
