"""The Forecast lab page (story P2b, screen W3b; contract `FnoForecastLab`, page `forecast_lab`): what each forecaster
said on the session and how each scores, per v3 question, from G4's report and the committed records
(`forecast_lab_inputs.py`).

- **v3 only in the questions:** protocol v4 is listed with its question ids, as a draft until its freeze record's day
  and as frozen with its protocol commit from then (G6 freeze; orchestrator, 25 Oct 2026); no V question is shown yet:
  v4's per-question entries are P2b's open work (no draft numbers and no invented minimum on a public page).
- **The standing** is G4's own sentence: forecasts are secondary to net profit and never promote a book."""

from __future__ import annotations

from ..forecast_scoring.score_report import STANDING
from .blocks import BlockBuilder, SessionRows
from .forecast_lab_forecasters import forecasters
from .forecast_lab_inputs import ForecastLabInputs
from .forecast_lab_questions import questions
from .forecast_questions import V3_QUESTIONS

V4_IDS = ("V1", "V2", "V3", "V4", "V5", "V6_1d", "V6_5d", "V7")  # V4_QUESTIONS in order (V6: one session, five)


class FnoForecastLabBlock(BlockBuilder):
    page_key, served_schema = "forecast_lab", "FnoForecastLabResponse"

    def build(self, rows: SessionRows) -> dict:
        return forecast_lab(rows.forecast_lab)


def forecast_lab(inputs: ForecastLabInputs) -> dict:
    report = inputs.report or {}
    return {
        "standing": report.get("standing", STANDING),  # G4's own sentence, also before its first report
        "protocols": _protocols(report, inputs),
        "forecasters": forecasters(inputs),
        "questions": questions(inputs),
    }


def _protocols(report: dict, inputs: ForecastLabInputs) -> list[dict]:
    v3_commit = (report.get("inputs") or {}).get("protocol_v3_commit")
    v3 = {"version": "v3", "status": "frozen" if v3_commit else "draft", "frozen_commit": v3_commit,
          "questions": [contract_id for contract_id, _ in V3_QUESTIONS.values()]}  # fmt: skip
    v4_commit = inputs.v4_freeze.commit if inputs.v4_freeze else None
    v4 = {"version": "v4", "status": "frozen" if v4_commit else "draft", "frozen_commit": v4_commit,
          "questions": list(V4_IDS)}  # fmt: skip
    return [v3, v4]
