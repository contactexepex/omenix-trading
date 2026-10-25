"""F1's push receipts in a rehearsal (story REH1b), chosen by each of their builders: GitHub's activity log in a real
run, the rehearsal origin's push log when rehearsing."""

from __future__ import annotations

import os
from collections.abc import Mapping

from .mode import rehearsal


def rehearsed_receipts(receipts, history, env: Mapping[str, str] = os.environ):
    mode = rehearsal(env)
    if mode is None:
        return receipts
    from .push_receipts import PUSH_LOG, LocalPushReceipts

    return LocalPushReceipts(mode.state / PUSH_LOG, history)
