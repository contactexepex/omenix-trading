"""A rehearsing process's set-up (story REH1), at `python -m fno`'s start: the shared replay clock and the HTTP guard.
Nothing in a real run."""

from __future__ import annotations

import os
from collections.abc import Mapping

from ..models import install_clock
from .clock import ReplayClock
from .mode import rehearsal


def install_process(env: Mapping[str, str] = os.environ) -> None:
    mode = rehearsal(env)
    if mode is None:
        return
    from . import http_guard

    install_clock(ReplayClock(mode.state))
    http_guard.install()
