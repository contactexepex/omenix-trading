"""Story R1d, step 0 (first part): today's exact Groww pacing, rate-limit pause and close-read retry behaviour, pinned
BEFORE they move onto the shared resilience layer. Offline: no Groww call, no real sleep, no clock. Passes on `main`
unchanged; the refactor keeps it green or states, in the R1d story, what changed and why."""

from __future__ import annotations

import threading
from datetime import date, datetime

import pytest

from fno.ingestion.close_read import reader as close_reader
from fno.ingestion.close_read.answer import Refused
from fno.ingestion.close_read.constants import TRIES, TRY_GAP_SECONDS
from fno.ingestion.intraday.candle_source import MIN_GAP_SECONDS, CandleCallFailed, GrowwCandleSource
from fno.ingestion.intraday.pacing import RatePacer
from fno.ingestion.providers.groww_quiet_windows import GrowwQuietWindow, QuietWindows
from fno.ingestion.providers.groww_rate_guard import (
    PAUSE_SECONDS,
    GrowwRateLimited,
    GrowwRateLimitPaused,
    RateGuardedGroww,
    RateLimitPause,
)

# ---- RatePacer (intraday) ---------------------------------------------------------------------------------------


class Moment:
    def __init__(self):
        self.now, self.slept = 100.0, []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def test_rate_pacer_spaces_starts_by_the_reciprocal_of_the_rate():
    m = Moment()
    pacer = RatePacer(4, m.clock, m.sleep)
    for _ in range(4):
        pacer.wait()
    assert pacer.interval == 0.25 and m.slept == [0.25, 0.25, 0.25]  # the first start is free


def test_rate_pacer_does_not_wait_after_an_idle_gap():
    m = Moment()
    pacer = RatePacer(2, m.clock, m.sleep)
    pacer.wait()
    m.now += 5
    pacer.wait()
    assert m.slept == []


def test_rate_pacer_holds_spacing_across_threads():
    """Deterministic: a frozen clock, and the waits the pacer asks for are the slots it handed out (6 callers, 0.05 s
    apart; the first is free). Timing callers after they wake would let scheduler jitter under load shrink the gap."""
    asked, lock = [], threading.Lock()

    def record(seconds):
        with lock:
            asked.append(seconds)

    pacer = RatePacer(20, clock=lambda: 0.0, sleep=record)
    threads = [threading.Thread(target=pacer.wait) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(asked) == pytest.approx([0.05 * n for n in range(1, 6)])


# ---- the 429 pause and the guard ---------------------------------------------------------------------------------


class Code429(Exception):
    code = "429"


class Other(Exception):
    code = "500"


class Client:
    EXCHANGE_NSE = "NSE"

    def __init__(self, error=None):
        self.error, self.calls = error, 0

    def quote(self, *args, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return {"ltp": 1}


def guarded(client, clock, quiet=None):
    return RateGuardedGroww(lambda: client, RateLimitPause(clock=clock), quiet)


def test_the_pause_is_sixty_seconds_after_a_429_and_ends_exactly_then():
    assert PAUSE_SECONDS == 60
    now = [1000.0]
    client = Client(Code429("raw Groww text with secret"))
    g = guarded(client, lambda: now[0])
    with pytest.raises(GrowwRateLimited) as limited:
        g.quote()
    assert "secret" not in str(limited.value) and limited.value.__cause__ is None  # Groww's text is never carried
    now[0] += 59
    with pytest.raises(GrowwRateLimitPaused):
        g.quote()
    assert client.calls == 1  # nothing reached Groww during the pause
    now[0] += 1
    client.error = None
    assert g.quote() == {"ltp": 1} and client.calls == 2


def test_the_wait_text_counts_the_seconds_left():
    now = [0.0]
    g = guarded(Client(Code429()), lambda: now[0])
    with pytest.raises(GrowwRateLimited):
        g.quote()
    now[0] += 20
    with pytest.raises(GrowwRateLimitPaused, match="paused for 40 s"):
        g.quote()


def test_other_errors_pass_through_unchanged_and_start_no_pause():
    now = [0.0]
    client = Client(Other("boom"))
    g = guarded(client, lambda: now[0])
    with pytest.raises(Other):
        g.quote()
    client.error = None
    assert g.quote() == {"ltp": 1}


def test_a_code_may_be_an_int_and_a_missing_code_is_not_a_rate_limit():
    class IntCode(Exception):
        code = 429

    g = guarded(Client(IntCode()), lambda: 0.0)
    with pytest.raises(GrowwRateLimited):
        g.quote()
    g = guarded(Client(RuntimeError("x")), lambda: 0.0)
    with pytest.raises(RuntimeError):
        g.quote()


def test_constants_pass_as_they_are_and_a_quiet_window_refuses_before_the_call():
    class Closed(QuietWindows):
        def wait(self):
            pass

        def check(self):
            raise GrowwQuietWindow("inside a mark")

    client = Client()
    assert guarded(client, lambda: 0.0).EXCHANGE_NSE == "NSE"
    with pytest.raises(GrowwQuietWindow):
        guarded(client, lambda: 0.0, Closed()).quote()
    assert client.calls == 0


def test_a_quiet_window_is_checked_before_the_pause():
    class Closed(QuietWindows):
        def wait(self):
            pass

        def check(self):
            raise GrowwQuietWindow("inside a mark")

    now = [0.0]
    pause = RateLimitPause(clock=lambda: now[0])
    pause.start()  # a 429 pause is running as well
    g = RateGuardedGroww(lambda: Client(), pause, Closed())
    with pytest.raises(GrowwQuietWindow):
        g.quote()


# ---- the candle source's own pace and failures ------------------------------------------------------------------


class Api:
    EXCHANGE_NSE, SEGMENT_CASH = "NSE", "CASH"
    CANDLE_INTERVAL_MIN_15, CANDLE_INTERVAL_MIN_1 = "i15", "i1"

    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def get_historical_candles(self, **kw):
        self.calls += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def source(answer, m):
    return GrowwCandleSource(Api(answer), lambda: datetime(2026, 10, 27, 16, 0), m.sleep, m.clock)


def test_candle_calls_start_at_least_half_a_second_apart():
    assert MIN_GAP_SECONDS == 0.5
    m = Moment()
    s = source({"candles": []}, m)
    s.candles(date(2026, 10, 1), date(2026, 10, 2))
    s.minute_candles(date(2026, 10, 2))
    s.minute_candles(date(2026, 10, 2))
    assert m.slept == [0.5, 0.5]


def test_a_failed_candle_call_names_the_class_only_never_the_text():
    m = Moment()
    with pytest.raises(CandleCallFailed) as failed:
        source(ValueError("token abc123"), m).candles(date(2026, 10, 1), date(2026, 10, 2))
    assert "abc123" not in str(failed.value) and "ValueError" in str(failed.value)
    assert failed.value.__cause__ is None


@pytest.mark.parametrize("answer", [{}, {"candles": None}, [], "x"])
def test_an_answer_without_a_candle_list_is_a_failed_call(answer):
    with pytest.raises(CandleCallFailed, match="no candle list"):
        source(answer, Moment()).candles(date(2026, 10, 1), date(2026, 10, 2))


# ---- the close reader's three tries ----------------------------------------------------------------------------


class Answers:
    def __init__(self, *steps):
        self.steps, self.calls = list(steps), 0

    def answer(self):
        self.calls += 1
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def reader(steps, monkeypatch):
    waits = []
    monkeypatch.setattr(close_reader, "read_answer", lambda payload, day: f"read:{payload}")
    r = close_reader.CloseReader(Answers(*steps), None, None, None, lambda: None, waits.append)
    return r, waits


def test_the_close_read_makes_three_tries_sixty_seconds_apart(monkeypatch):
    assert (TRIES, TRY_GAP_SECONDS) == (3, 60)
    r, waits = reader([Refused("not today's close")] * 3, monkeypatch)
    got, raw, reason = r._read(date(2026, 10, 27))
    assert got is None and raw == b"" and reason == "not today's close"
    assert waits == [60, 60] and r.source.calls == 3  # no wait after the last try


def test_the_close_read_stops_at_the_first_good_answer(monkeypatch):
    r, waits = reader([Refused("early"), ({"x": 1}, b"raw")], monkeypatch)
    got, raw, reason = r._read(date(2026, 10, 27))
    assert got == "read:{'x': 1}" and raw == b"raw" and reason == "" and waits == [60]


def test_an_unexpected_error_is_reported_by_class_with_the_message_withheld(monkeypatch):
    r, waits = reader([RuntimeError("https://secret-url")] * 3, monkeypatch)
    _, _, reason = r._read(date(2026, 10, 27))
    assert reason == "RuntimeError (message withheld)" and waits == [60, 60]
