"""Composition root for the 3 pm parts after NIFTY's push (stories A4c and A4f): one recorder per traded index and the
NIFTY weekly one, on the 3 pm recorder's own provider, sharing one reader of NSE's daily files (parsed once a run);
the indices in A4's Drive-only quote store, the weeklies in their own. Apart from `fno/composition.py`, which is at
the size limit."""

from __future__ import annotations

from ..constants import RECORDED_INDEX_OPTIONS
from ..providers import AUTO_PROVIDER, get_provider
from ..storage.quote_wiring import build_drive_only_quote_store
from ..storage.wiring import QUOTES_FOLDER, build_nse_fo_library, build_quote_store, build_session_calendar
from .expiry_listing import NseDailyFileExpiries
from .indices import index_slot, weekly_slot
from .recorder import QuoteSnapshotRecorder
from .weekly import WEEKLY_DATASET, WEEKLY_NAME


def build_index_quote_recorders(cfg: dict) -> dict[str, QuoteSnapshotRecorder]:
    """In the order they run: BANKNIFTY, FINNIFTY, MIDCPNIFTY, then NIFTY's weeklies."""
    provider = get_provider(cfg.get("quotes", {}).get("provider", AUTO_PROVIDER), cfg)
    expiries, calendar = NseDailyFileExpiries(build_nse_fo_library()), build_session_calendar()
    shared = {"fallback": expiries, "calendar": calendar, "history": expiries}
    store = build_quote_store()
    recorders = {
        u: QuoteSnapshotRecorder(provider, store, slot=index_slot(u), **shared) for u in RECORDED_INDEX_OPTIONS
    }
    weekly_store = build_drive_only_quote_store(QUOTES_FOLDER, dataset=WEEKLY_DATASET)  # its quote files: Drive only
    recorders[WEEKLY_NAME] = QuoteSnapshotRecorder(
        provider, weekly_store, dataset=WEEKLY_DATASET, slot=weekly_slot(), **shared
    )  # fmt: skip
    from ..rehearsal.quote_wiring import rehearsed_recorder

    return {name: rehearsed_recorder(recorder) for name, recorder in recorders.items()}  # REH1b: recorded, rehearsing
