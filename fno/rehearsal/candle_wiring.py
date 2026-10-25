"""A16b's candle source in a rehearsal (story REH1b), chosen by `build_candle_backfill`: Groww in a real run, the
day's recorded answers when rehearsing (the record checkout's manifests, the real Drive's raw copies, read-only). The
live source is passed as its builder and built only in a real run, so a rehearsal never needs the Groww SDK it never
calls (REH1j's dry run, 24 Oct: `GrowwProvider(cfg)` raised "Install the Groww SDK first" before the recorded source
replaced it)."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping

from .mode import rehearsal


def rehearsed_candle_source(live: Callable[[], object], env: Mapping[str, str] = os.environ):
    """`live`: builds the live source (Groww); called only in a real run."""
    mode = rehearsal(env)
    if mode is None:
        return live()
    from ..config import ROOT
    from ..intraday.backfill_daily import MANIFESTS
    from ..models import now_ist
    from ..storage.wiring import MANIFEST_FOLDER, RAW_AREA
    from .record_drive import RecordFiles
    from .recorded_candles import RecordedCandles

    manifests = mode.record / MANIFEST_FOLDER.relative_to(ROOT) / MANIFESTS
    return RecordedCandles(manifests, RecordFiles(RAW_AREA), now_ist, time.sleep)  # Drive at the first read
