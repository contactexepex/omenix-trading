"""Composition root for a named 3 pm capture (story A4e): A4's recorder on the 3 pm provider, in the window's own
dataset, with no request after the window's end, and each chain call, the level reads and A16's clock check timed
into its sidecar. Apart from `fno/composition.py`, which is at the size limit."""

from __future__ import annotations

from dataclasses import replace

from fno.ingestion.intraday.clock_wiring import build_clock_check
from fno.ingestion.providers import AUTO_PROVIDER, get_provider
from fno.ingestion.providers.public import PublicData
from fno.ingestion.quotes.capture_log import CaptureLog, TimedLevels, TimedProvider
from fno.ingestion.quotes.expiry_listing import NseDailyFileExpiries
from fno.ingestion.quotes.market_levels import NseLevelSource
from fno.ingestion.quotes.recorder import DATASET, QuoteSnapshotRecorder
from fno.ingestion.quotes.slot import NIFTY_SLOT
from fno.ingestion.quotes.window import named_window
from fno.ingestion.storage.quote_wiring import build_drive_only_quote_store
from fno.ingestion.storage.wiring import QUOTES_FOLDER, build_nse_fo_library, build_session_calendar
from fno.shared.models import now_ist


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
