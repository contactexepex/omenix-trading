"""A4h's index-list source in a rehearsal (story REH1b), chosen by `build_close_reader`: NSE in a real run, the day's
recorded answers when rehearsing (the record checkout's receipts, the real Drive's raw files, read-only)."""

from __future__ import annotations

import os
import time
from collections.abc import Mapping

from .mode import rehearsal

RECEIPTS = "receipts"


def rehearsed_close_list(source, drive, env: Mapping[str, str] = os.environ):
    mode = rehearsal(env)
    if mode is None:
        return source
    from ..models import now_ist
    from ..storage.receipts import ReceiptFolder
    from .recorded_closes import RecordedCloseList

    return RecordedCloseList(ReceiptFolder(mode.record / RECEIPTS), drive.record_view().get, now_ist, time.sleep)
