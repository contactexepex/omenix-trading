"""Story G13's fixed values (`fno/constants.py` is at its size limit, as `fno/forecast_v4_rules/constants.py`)."""

from __future__ import annotations

from ..constants import BOOK2_HYBRID, BOOK3_AI

METHOD_VERSION = "g13_v1"

# Forecasters (G13 section 3); the AI books' ids are imported, never retyped (G11's owner, 16 Oct)
IMPLIED, RV20, HIST750 = "implied", "rv20", "hist750"
RULE_FORECASTERS = (IMPLIED, RV20, HIST750)
AI_SLOTS = (BOOK2_HYBRID, BOOK3_AI)  # slots only: no rows, no start date, never a miss
FORECASTERS = RULE_FORECASTERS + AI_SLOTS

# Horizons: regular sessions after the day, and the near and next monthly expiry sessions
H1, H5, E1, E2 = "h1", "h5", "e1", "e2"
SESSION_HORIZONS = {H1: 1, H5: 5}
HORIZONS = (H1, H5, E1, E2)

FORECAST_LEVELS = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)
DISTRIBUTION_LEVELS = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)

# Row statuses and labels (section 4)
OK, MISSING, NOT_ELIGIBLE, NOT_STARTED = "ok", "missing", "not_eligible", "not_started"  # not_started: AI slots
LIVE, BACKFILL_3PM, BACKFILL_EOD = "live", "backfill_3pm", "backfill_eod"
LABELS = (LIVE, BACKFILL_3PM, BACKFILL_EOD)
BODY, TAIL = "body", "tail"

# Chain inputs (section 1): the quote filter, the forward, the tails' strike gap
SPREAD_SHARE, SPREAD_FLOOR_RS = 0.10, 0.50  # ask - bid <= max(10% of mid, Rs 0.50)
EOD_MIN_PRICE_RS = 0.50
FORWARD_STRIKES = 3
MAX_STRIKE_GAP = 200.0
MIN_CDF_POINTS = 8
MAX_MEAN_GAP = 0.005  # |mean / F - 1|
MIN_SMILE_POINTS = 5
DAYS_PER_YEAR = 365
DELTA_POINTS = {"10P": -0.10, "25P": -0.25, "25C": 0.25, "10C": 0.10}

# Baselines (section 3)
RV_WINDOW, RV_YEAR = 20, 252
HIST_WINDOW, HIST_MINIMUM = 750, 500

SOURCE_GROWW, SOURCE_NSE, SOURCE_PANEL = "groww", "nse", "panel"
SMILE_VALUE_NOTE = (
    "smile_value is Black-76 at a quadratic smile fitted to the same day's quotes: a smoothness residual, not a "
    "valuation and no trade signal (a contract off the curve is usually a stale or wide quote)"
)
RISK_NEUTRAL_NOTE = "risk-neutral distribution from option prices, not a forecast of where the index will be"
