"""The five v3 forecast questions as the F&O screens name them (story P2): G4's question id -> the contract's id and
the question in plain words, the Forecast lab's own text (contract 2.9, `FnoForecastHistoryQuestion.plain`). One table
for every page that names a v3 question, so the screens never word a question two ways."""

from __future__ import annotations

from ..constants import (
    FORECAST_Q1_UP_20D,
    FORECAST_Q2_MOVE_3PCT_20D,
    FORECAST_Q3_RV_RISES_20D,
    FORECAST_Q4_VIX_UP_10D,
    FORECAST_Q5_RV_BELOW_IV,
)

V3_QUESTIONS = {  # in the Forecast lab's order
    FORECAST_Q1_UP_20D: ("Q1", "Will NIFTY be higher in 20 sessions?"),
    FORECAST_Q2_MOVE_3PCT_20D: ("Q2", "Will NIFTY move at least 3% either way over the next 20 sessions?"),
    FORECAST_Q3_RV_RISES_20D: ("Q3", "Will NIFTY swing more over the next 20 sessions than over the last 20?"),
    FORECAST_Q4_VIX_UP_10D: ("Q4", "Will India VIX be higher in 10 sessions?"),
    FORECAST_Q5_RV_BELOW_IV: ("Q5", "Will NIFTY swing less over the next 20 sessions than its options price in today?"),
}
