"""Story G13b's fixed values (`fno/constants.py` is at its size limit)."""

from __future__ import annotations

from datetime import time

from ..constants import BOOK2_HYBRID, BOOK3_AI, NIFTY_SYMBOL

METHOD_VERSION = "g13b_v1"
SCHEMA = "g13b_ranges_v1"
UNDERLYINGS = (NIFTY_SYMBOL, "BANKNIFTY")

ISSUE_0915, ISSUE_0930, ISSUE_1545 = "0915", "0930", "1545"
ISSUES = (ISSUE_0915, ISSUE_0930, ISSUE_1545)  # 0915 is part C, 0930 not built (question 1): the schema keeps both
N0, N1, N3 = "N0", "N1", "N3"
HORIZON_SESSIONS = {N0: 0, N1: 1, N3: 3}
HORIZONS_AT = {ISSUE_1545: (N1, N3)}  # no N0 at 15:45: the day has closed

LEVELS = (0.05, 0.25, 0.50, 0.75, 0.95)

IMPLIED, RV20, HIST750, EWMA_T4, NO_CHANGE = "implied", "rv20", "hist750", "ewma_t4", "no_change"
RULE_FORECASTERS = (IMPLIED, RV20, HIST750, EWMA_T4, NO_CHANGE)
SLOTS = (BOOK2_HYBRID, BOOK3_AI)  # and the v4 rule forecasters later: no rows, no start date, never a miss
FORECASTERS = RULE_FORECASTERS + SLOTS

OK, MISSING, NOT_ELIGIBLE = "ok", "missing", "not_eligible"
LIVE, BACKFILL_EOD, BACKFILL_3PM = "live", "backfill_eod", "backfill_3pm"
LABELS = (LIVE, BACKFILL_EOD, BACKFILL_3PM)

# τ from the 3 pm capture: the rest of the session, intraday share even in time (A1, revision 3)
OVERNIGHT_SHARE = 0.393  # measured: A16b candle RV, 1,469 sessions 2020-2025 (story text); frozen in the method
REST_OF_DAY = (1 - OVERNIGHT_SHARE) * 30 / 375

DEADLINE = time(9, 15)  # a 15:45 issue is sealed by 09:15 IST of the next regular session

BRIER_NOTE = "rv20, ewma_t4 and no_change say P(up) = 0.5: their Brier is always 0.25 and tests nothing about direction"
TAU_NOTE = "tau from the 3 pm capture adds (1 - 0.393) x 30/375 = 0.049 sessions; 0.393 is the frozen overnight share"
QS_NOTE = "QS = (2/5) x the sum of the pinball losses over 5 levels, in log units: a coarse CRPS approximation"
