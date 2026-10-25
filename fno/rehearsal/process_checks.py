"""What a rehearsing process must be, checked inside one (story REH1a, judge 557 SF1): its clock is the shared replay
clock, at the replay time, and a live call is refused by the rehearsal's own refusal before it is made. Run in a
`python -m fno rehearse check` child, so the package's real entry point is what is checked."""

from __future__ import annotations

from datetime import timedelta

from .. import models
from .clock import ReplayClock
from .mode import Rehearsal

LIVE_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
NOT_REPLAY_CLOCK = "rehearsal guard: this process's clock is {found}, not the replay clock"
OFF_REPLAY_TIME = "rehearsal guard: this process reads {seen}, the replay clock {replay}"
LIVE_NOT_REFUSED = "rehearsal guard: a live call was not refused by the rehearsal ({outcome})"
TOLERANCE = timedelta(seconds=60)


def process_problems(mode: Rehearsal) -> list[str]:
    found = []
    if not isinstance(models._clock, ReplayClock):
        found.append(NOT_REPLAY_CLOCK.format(found=getattr(models._clock, "__name__", type(models._clock).__name__)))
    seen, replay = models.now_utc(), ReplayClock(mode.state)()
    if abs(seen - replay) > TOLERANCE:
        found.append(OFF_REPLAY_TIME.format(seen=seen.isoformat(), replay=replay.isoformat()))
    outcome = _live_call()
    if outcome:
        found.append(LIVE_NOT_REFUSED.format(outcome=outcome))
    return found


def _live_call() -> str:
    """ "" when the rehearsal refused it; otherwise what happened instead."""
    import requests

    from .http_guard import RehearsalCallRefused

    try:
        requests.get(LIVE_URL, timeout=3)
    except RehearsalCallRefused:
        return ""
    except Exception as other:  # noqa: BLE001 - anything but the refusal means the call was attempted
        return f"it was attempted: {type(other).__name__}"
    return "it was answered"
