"""G13c's fixed strings and numbers (story text, sections 1-2)."""

from __future__ import annotations

MEASURE = "risk-neutral (market-implied), not a forecast"
BODY, TAIL = "body", "tail"  # the strike inside the measured CDF, or where the lognormal tail rule decides
SOURCE_3PM, SOURCE_EOD, SOURCE_ALL = "3pm", "backfill_eod", "all"
SOURCE_OF_LABEL = {"live": SOURCE_3PM, "backfill_3pm": SOURCE_3PM, "backfill_eod": SOURCE_EOD}  # G13's labels
SOURCE_PREFERENCE = (SOURCE_3PM, SOURCE_EOD)  # "all": one row set per day and expiry, the 3 pm chain first

HORIZON_BUCKETS = ((1, 7), (8, 21), (22, 45), (46, None))  # calendar days to expiry, both ends included
BIN_EDGES = (0.0, 0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.0)  # the last bin includes 1

DRAWS, SEED = 2000, 20261022  # the cluster bootstrap over expiries (fixed seed: a rerun is byte-identical)
INTERVAL = (2.5, 97.5)  # percentiles of the 95% interval
PAISA = 0.005  # settlement and close agree when they differ by less than half a paisa

SETTLED_STTLM, SETTLED_FUTIDX = "udiff", "futidx_settle"  # E7's UDiFF reader; the legacy FUTIDX row
CLOSE_MISMATCH, NOT_SETTLED_YET, REFUSED, NO_CLOSE_CHECK = "close_mismatch", "unsettled", "refused", "no_close"

SCHEMA = "g13c_calibration_v1"
EXPLORATORY = (
    "exploratory: NIFTY's 2019-26 monthlies are already marked spent in research/DATA_SPEND.md; a forecaster built on "
    "this report records this use there"
)
TAIL_NOTE = "tail strikes are shown per contract but not calibrated: the rows use only strikes inside the measured CDF"
UNIT_NOTE = "the unit is the expiry: every interval resamples whole expiries, never rows"
