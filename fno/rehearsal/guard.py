"""The rehearsal's guard (story REH1, acceptance 1-4b): before the first step, every outside service is built through
the real composition roots with the mode set, and each must be its rehearsal form. Any problem stops the rehearsal
before anything is written. A planted break of each check is caught by its test."""

from __future__ import annotations

from collections.abc import Callable

from .alert_label import LabelledAlerts
from .card_label import LabelledCardPoster, RehearsalCardClocks
from .drive import DryrunDrive
from .http_guard import allowed
from .report_label import LabelledReportPoster

LIVE_PROBES = ("https://www.nseindia.com/api/option-chain-indices", "https://api.groww.in/v1/live-data/quote",
               "https://api.anthropic.com/v1/messages", "https://api.github.com/repos/x/y/dispatches",
               "https://query1.finance.yahoo.com/v8/finance/chart/x",
               "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_20261023_F_0000.csv.zip",
               "https://api.github.com/repos/exepex/omenix-trading/activity")  # fmt: skip
NOT_REHEARSED = "rehearsal guard: {what} is {found}, not its rehearsal form"
LIVE_ALLOWED = "rehearsal guard: a live call would be allowed: {url}"


def builders() -> dict[str, tuple[Callable[[], object], tuple[type, ...]]]:
    """Each outside service's real builder and the rehearsal forms it must return (None: no service set up here)."""
    from ..cards.wiring import build_card_clocks, build_card_poster
    from ..composition import build_alert_sender, build_nse_quote_recorder, build_quote_recorder
    from ..config import load_app_config
    from ..constants import RECORDED_INDEX_OPTIONS
    from ..forecast_lab.wiring import build_forecast_poster
    from ..intraday.clock_wiring import build_clock_check
    from ..quotes.index_wiring import build_index_quote_recorders
    from ..quotes.weekly import WEEKLY_NAME
    from ..quotes.window import V4_WINDOW
    from ..quotes.window_wiring import build_window_quote_recorder
    from ..storage.raw_source import NseDailyFoSource
    from ..storage.wiring import build_nse_source, build_owner_drive
    from .preopen_wiring import RehearsalClockCheck
    from .recorded_archive import RecordedArchiveSession
    from .recorded_quotes import RecordedRecorder

    def index_recorder(name: str):
        return lambda: build_index_quote_recorders(load_app_config())[name]

    indices = {
        f"{name}'s 3 pm recorder": (index_recorder(name), (RecordedRecorder,))
        for name in (*RECORDED_INDEX_OPTIONS, WEEKLY_NAME)
    }  # fmt: skip; REH1s: A4c's and A4f's
    return {
        "the owner's Drive": (build_owner_drive, (DryrunDrive, type(None))),
        "the #fno-desk alerts": (build_alert_sender, (LabelledAlerts,)),
        "the card's poster": (build_card_poster, (LabelledCardPoster,)),
        "the lab's poster": (build_forecast_poster, (LabelledReportPoster,)),
        "the 3 pm recorder": (lambda: build_quote_recorder(load_app_config()), (RecordedRecorder,)),  # REH1b
        "NSE's 3 pm recorder": (lambda: build_nse_quote_recorder(load_app_config()), (RecordedRecorder,)),  # O6
        "NSE's archive session": (lambda: build_nse_source(NseDailyFoSource).session, (RecordedArchiveSession,)),
        "A16's clock check": (build_clock_check, (RehearsalClockCheck,)),  # REH1c
        "the card's clocks": (build_card_clocks, (RehearsalCardClocks,)),  # T1f
        **indices,
        "the v4 window's recorder": (
            lambda: build_window_quote_recorder(load_app_config(), V4_WINDOW),
            (RecordedRecorder,),
        ),  # fmt: skip; REH1s: A4e's, G10's capture
    }


def problems(services=None, probes=LIVE_PROBES, is_allowed=allowed) -> list[str]:
    found = []
    for what, (build, forms) in (services or builders()).items():
        built = build()
        if not isinstance(built, forms):
            found.append(NOT_REHEARSED.format(what=what, found=type(built).__name__))
    found += [LIVE_ALLOWED.format(url=url) for url in probes if is_allowed("GET", url)]
    return found
