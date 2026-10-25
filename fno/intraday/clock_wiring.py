"""A16's checked clock (the host clock against GitHub's and Slack's `Date` headers), built in one place for every user:
A16's 15-minute recorder and A4e's named 3 pm captures (one rule, no copy). Apart from `wiring.py`, so the 3 pm
recorder does not import A16's Groww intraday graph."""

from __future__ import annotations

import os

from ..constants import DEFAULT_REPOSITORY, GITHUB_REPOSITORY_VARIABLE
from ..models import now_ist
from ..server_clock import GITHUB_TIME_URL, SLACK_TIME_URL, HttpDateClock
from .clock import ClockCheck


def build_clock_check() -> ClockCheck:
    repository = os.environ.get(GITHUB_REPOSITORY_VARIABLE) or DEFAULT_REPOSITORY
    github = HttpDateClock("github", GITHUB_TIME_URL.format(repository=repository))
    from ..rehearsal.preopen_wiring import rehearsed_clock_check

    return rehearsed_clock_check(ClockCheck([github, HttpDateClock("slack", SLACK_TIME_URL)], now_ist))  # REH1c
