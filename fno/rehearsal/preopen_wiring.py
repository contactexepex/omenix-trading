"""A22's parts and A16's clock check in a rehearsal (story REH1c), chosen by `fno/preopen/wiring.py` and
`build_clock_check`: the day's recorded answers in place of NSE's and Groww's live reads; the clock check says plainly
that a replay clock is not checked against GitHub's and Slack's servers (it would always read as a skew)."""

from __future__ import annotations

import os
import time
from collections.abc import Mapping

from ..intraday.clock import CLOCK_UNCHECKED, ClockCheck, ClockReading
from .mode import rehearsal

RECEIPTS = "receipts"
NOT_CHECKED = "rehearsal: replay clock, not checked against GitHub's and Slack's servers"


def rehearsed_preopen_parts(parts: list, env: Mapping[str, str] = os.environ) -> list:
    mode = rehearsal(env)
    if mode is None:
        return parts
    from ..models import now_ist
    from ..storage.receipts import ReceiptFolder
    from .record_drive import RecordFiles
    from .recorded_preopen import RecordedPreopenPart

    receipts, read = ReceiptFolder(mode.record / RECEIPTS), RecordFiles("")
    return [RecordedPreopenPart(part, receipts, read, now_ist, time.sleep) for part in parts]


class RehearsalClockCheck(ClockCheck):
    def __init__(self):
        super().__init__([], lambda: None)

    def check(self) -> ClockReading:
        return ClockReading(CLOCK_UNCHECKED, ())  # no checks, so no warning: not a capture problem (REH1l)


def rehearsed_clock_check(check: ClockCheck, env: Mapping[str, str] = os.environ) -> ClockCheck:
    return check if rehearsal(env) is None else RehearsalClockCheck()
