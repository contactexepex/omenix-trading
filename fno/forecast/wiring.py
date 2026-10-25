"""Composition root of the forecasts (epic G): the only place that picks the forecast code's concrete classes, like
`fno/risk/wiring.py` for the risk manager."""

from __future__ import annotations

from ..research_data.panel_reader import read_nifty_panel
from ..research_engine.implied_vol import Black76
from ..storage.wiring import PANEL_FOLDER, build_session_calendar
from .golden import golden_rows
from .iv30 import PanelAtmIv30

GOLDEN_OPTION_DAYS = 100  # IV30 reads only monthly expiries, all within about 95 days


def build_atm_iv30(cfg: dict) -> PanelAtmIv30:
    """Story G1: the 30-day ATM IV on B1's Black-76 model and `risk_free_rate`."""
    return PanelAtmIv30(Black76(), cfg["risk_free_rate"])


def forecast_golden_rows(cfg: dict, years: list[int]) -> list[dict[str, str]]:
    """The forecast protocol's golden IV30 and RV20 values (judge 47), one panel year at a time to bound memory."""
    rows, estimator, calendar = [], build_atm_iv30(cfg), build_session_calendar()
    for year in years:
        panel = read_nifty_panel(PANEL_FOLDER, [year], keep=lambda d, e: (e - d).days <= GOLDEN_OPTION_DAYS)
        rows += golden_rows(panel, calendar, estimator)
    return rows
