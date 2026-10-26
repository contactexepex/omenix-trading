"""Story R1b, step 0: today's exact NSE download behaviour, pinned BEFORE the refactor onto the shared resilience layer.

Every test here passes on `main` unchanged; the refactor must keep them green. They pin wait sequences, error
classification, the 429 rule, Retry-After handling and what is raised with which try count. No real NSE call, no
real sleep. If one of these changes, behaviour changed: that needs a reason in the story, not a test edit."""

from __future__ import annotations

from datetime import date

import pytest
import requests

from fno.ingestion.storage.raw_source import (
    NseDailyFoSource,
    RawFileRefused,
    RawSourceCoolingOff,
    RawSourceUnavailable,
)
from fno.shared.http_pacing import SourceCoolingOff

DAY = date(2026, 10, 12)
PATH = NseDailyFoSource.path_for(DAY)


class ScriptedSession:
    """Answers each call from a script of responses or exceptions, and records how many calls were made."""

    def __init__(self, script):
        self.script, self.calls = list(script), 0

    def get(self, url, timeout=None):
        self.calls += 1
        step = self.script.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step

    head = get


def run(http_fakes, script, now=None):
    waits: list[float] = []
    session = ScriptedSession(script)
    kwargs = {"clock": lambda: now} if now else {}
    source = NseDailyFoSource(session, sleep=waits.append, **kwargs)
    return source, session, waits


def response(http_fakes, status, **headers):
    return http_fakes.Response(status_code=status, content=b"data", headers=headers)


def test_server_error_four_tries_waiting_5_15_45(http_fakes):
    source, session, waits = run(http_fakes, [response(http_fakes, 503)] * 4)
    with pytest.raises(RawSourceUnavailable) as raised:
        source.fetch(PATH)
    assert waits == [5, 15, 45] and session.calls == 4 and raised.value.tries == 4
    assert raised.value.status == 503 and not isinstance(raised.value, RawFileRefused)


def test_recovery_after_one_server_error_waits_once(http_fakes):
    source, session, waits = run(http_fakes, [response(http_fakes, 500), response(http_fakes, 200)])
    assert source.fetch(PATH) == b"data" and waits == [5] and session.calls == 2


def test_no_connection_retries_on_the_same_waits_and_says_how_many_tries(http_fakes):
    source, session, waits = run(http_fakes, [requests.ConnectionError("boom")] * 4)
    with pytest.raises(RawSourceUnavailable, match="after 4 tries") as raised:
        source.fetch(PATH)
    assert waits == [5, 15, 45] and session.calls == 4 and raised.value.tries == 4 and raised.value.status is None


def test_timeout_then_success(http_fakes):
    source, _, waits = run(http_fakes, [requests.Timeout("slow"), response(http_fakes, 200)])
    assert source.fetch(PATH) == b"data" and waits == [5]


def test_two_429_in_a_row_stop_at_once_as_cooling_off(http_fakes):
    source, session, waits = run(http_fakes, [response(http_fakes, 429)] * 4)
    with pytest.raises(RawSourceCoolingOff) as raised:
        source.fetch(PATH)
    assert waits == [5] and session.calls == 2 and raised.value.tries == 2 and raised.value.status == 429


def test_a_429_followed_by_another_status_resets_the_429_count(http_fakes):
    script = [
        response(http_fakes, 429),
        response(http_fakes, 503),
        response(http_fakes, 429),
        response(http_fakes, 200),
    ]
    source, session, waits = run(http_fakes, script)
    assert source.fetch(PATH) == b"data" and waits == [5, 15, 45] and session.calls == 4


def test_403_is_refused_at_once_without_a_wait(http_fakes):
    source, session, waits = run(http_fakes, [response(http_fakes, 403), response(http_fakes, 200)])
    with pytest.raises(RawFileRefused) as raised:
        source.fetch(PATH)
    assert waits == [] and session.calls == 1 and raised.value.tries == 1 and raised.value.status == 403


@pytest.mark.parametrize("status", [400, 401, 418, 451])
def test_any_other_non_2xx_status_is_refused_never_retried(http_fakes, status):
    source, session, waits = run(http_fakes, [response(http_fakes, status)])
    with pytest.raises(RawFileRefused):
        source.fetch(PATH)
    assert waits == [] and session.calls == 1


def test_404_is_not_published_and_not_retried(http_fakes):
    source, session, waits = run(http_fakes, [response(http_fakes, 404)])
    assert source.fetch(PATH) is None and waits == [] and session.calls == 1


def test_retry_after_longer_than_the_schedule_stretches_the_wait(http_fakes):
    source, _, waits = run(http_fakes, [response(http_fakes, 503, **{"Retry-After": "30"}), response(http_fakes, 200)])
    assert source.fetch(PATH) == b"data" and waits == [30]


def test_retry_after_shorter_than_the_schedule_does_not_shorten_it(http_fakes):
    source, _, waits = run(http_fakes, [response(http_fakes, 503, **{"Retry-After": "2"}), response(http_fakes, 200)])
    assert source.fetch(PATH) == b"data" and waits == [5]


def test_retry_after_of_exactly_120_is_waited_but_121_stops_at_once(http_fakes):
    source, _, waits = run(http_fakes, [response(http_fakes, 503, **{"Retry-After": "120"}), response(http_fakes, 200)])
    assert source.fetch(PATH) == b"data" and waits == [120]
    source, session, waits = run(http_fakes, [response(http_fakes, 503, **{"Retry-After": "121"})])
    with pytest.raises(RawSourceUnavailable, match=r"Retry-After 121"):
        source.fetch(PATH)
    assert waits == [] and session.calls == 1


def test_retry_after_on_the_last_try_still_gives_up_without_a_wait(http_fakes):
    script = [response(http_fakes, 503)] * 3 + [response(http_fakes, 503, **{"Retry-After": "10"})]
    source, session, waits = run(http_fakes, script)
    with pytest.raises(RawSourceUnavailable):
        source.fetch(PATH)
    assert waits == [5, 15, 45] and session.calls == 4


def test_a_paused_host_raises_cooling_off_without_waiting(http_fakes):
    source, session, waits = run(http_fakes, [SourceCoolingOff("nse refused; not calling for 15 minutes")])
    with pytest.raises(RawSourceCoolingOff) as raised:
        source.fetch(PATH)
    assert waits == [] and session.calls == 1 and raised.value.tries == 0


def test_a_pause_that_starts_mid_retry_reports_the_tries_already_made(http_fakes):
    source, _, waits = run(http_fakes, [response(http_fakes, 503), SourceCoolingOff("paused")])
    with pytest.raises(RawSourceCoolingOff) as raised:
        source.fetch(PATH)
    assert waits == [5] and raised.value.tries == 1


def test_a_request_that_cannot_be_built_is_not_retried(http_fakes):
    source, session, waits = run(http_fakes, [requests.exceptions.InvalidURL("bad")])
    with pytest.raises(RawSourceUnavailable, match="not sent") as raised:
        source.fetch(PATH)
    assert waits == [] and session.calls == 1 and raised.value.tries == 1


def test_head_requests_follow_the_same_policy(http_fakes):
    source, _, waits = run(http_fakes, [response(http_fakes, 503), response(http_fakes, 200)])
    assert source.last_written(PATH) is None and waits == [5]
