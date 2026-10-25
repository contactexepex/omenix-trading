"""The forecast history page (story P2, contract 2.9 `FnoForecastHistory`, page `forecast_history`): for each v3
question, each forecaster's running score as G4's report of each day gives it (`scores[].primary`: scored, mean_brier).

- **Live and back-fill apart:** G4's `live_1500_proxy` mode is `live`, `close_proxy` is `backfill_exploratory`; a live
  series and a back-fill one are never joined.
- **One point per G4 report** (its as_of); a day without a report has no point, and a point needs n >= 1.
- **One back-fill file per series** (contract 2.10.0, `backfill_sha256`): a back-fill series names the file
  it was scored on (G4's `inputs.backfill_sha256`); when the file changes, the same forecaster starts a new series, so
  no series spans a rebuild (a rebuild moves every running average at once). A live series names none."""

from __future__ import annotations

from ..forecast_scoring.score_inputs import CLOSE_PROXY, LIVE
from .blocks import BlockBuilder, SessionRows
from .forecast_questions import V3_QUESTIONS

LABELS = {LIVE: "live", CLOSE_PROXY: "backfill_exploratory"}


class FnoForecastHistoryBlock(BlockBuilder):
    page_key, served_schema = "forecast_history", "FnoForecastHistoryResponse"

    def build(self, rows: SessionRows) -> dict:
        return forecast_history(rows.score_reports)


def forecast_history(reports: list[dict]) -> dict:
    points = _points(reports)
    questions = []
    for question, (contract_id, plain) in V3_QUESTIONS.items():
        series = [{"forecaster": f, "label": LABELS[mode], "backfill_sha256": sha, "points": p}
                  for (q, mode, f, sha), p in points.items() if q == question]  # fmt: skip
        if series:
            questions.append({"id": contract_id, "protocol": "v3", "plain": plain, "metric": "brier", "series": series})
    return {"questions": questions}


def _points(reports: list[dict]) -> dict[tuple, list[dict]]:
    """(question, mode, forecaster, back-fill file or None) -> the running score after each report, oldest first; by
    forecaster, then label, then file in the order it first appears."""
    out: dict[tuple, list[dict]] = {}
    for report in reports:
        backfill = report["inputs"].get("backfill_sha256")
        for mode in report["modes"]:
            if mode["mode"] not in LABELS:
                continue
            for score in mode["scores"]:
                summary = score["primary"]
                if summary["scored"] >= 1 and score["question"] in V3_QUESTIONS:
                    key = (score["question"], mode["mode"], score["forecaster"],
                           backfill if mode["mode"] == CLOSE_PROXY else None)  # fmt: skip
                    point = {"as_of": report["as_of"], "n": summary["scored"], "mean_loss": summary["mean_brier"]}
                    out.setdefault(key, []).append(point)
    return dict(sorted(out.items(), key=lambda item: (item[0][2], item[0][1])))
