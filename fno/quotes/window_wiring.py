"""Composition root for a named 3 pm capture (story A4e): A4's recorder on the 3 pm provider, in the window's own
dataset, with no request after the window's end, and each chain call, the level reads and A16's clock check timed
into its sidecar. Apart from `fno/composition.py`, which is at the size limit."""

from __future__ import annotations

from dataclasses import replace

from ..intraday.clock_wiring import build_clock_check
from ..models import now_ist
from ..providers import AUTO_PROVIDER, get_provider
from ..providers.public import PublicData
from ..storage.quote_wiring import build_drive_only_quote_store
from ..storage.wiring import QUOTES_FOLDER, build_nse_fo_library, build_session_calendar
from .capture_log import CaptureLog, TimedLevels, TimedProvider
from .expiry_listing import NseDailyFileExpiries
from .market_levels import NseLevelSource
from .recorder import DATASET, QuoteSnapshotRecorder
from .slot import NIFTY_SLOT
from .window import named_window


def build_window_quote_recorder(cfg: dict, name: str) -> QuoteSnapshotRecorder:
    """The same sources as A4's `build_quote_recorder`; raises ConfigError for an unknown or bad window before any
    of them is built or asked."""
    window = named_window(cfg, name)
    log = CaptureLog(build_clock_check(), now_ist, window.end)
    provider = TimedProvider(get_provider(cfg.get("quotes", {}).get("provider", AUTO_PROVIDER), cfg), log)
    expiries, dataset = NseDailyFileExpiries(build_nse_fo_library()), window.dataset(DATASET)
    store = build_drive_only_quote_store(QUOTES_FOLDER, dataset=dataset)  # the window's quote files to Drive only (A4b)
    return QuoteSnapshotRecorder(
        provider,
        store,
        fallback=expiries,
        calendar=build_session_calendar(),
        history=expiries,
        levels=TimedLevels(NseLevelSource(PublicData().nse_json), log),
        dataset=dataset,
        slot=replace(NIFTY_SLOT, stop_requests_at=window.end),
        window=window,
        log=log,
    )
