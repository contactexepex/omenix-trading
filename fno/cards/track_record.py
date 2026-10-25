"""A forecaster's track record as the card states it (design 07 section 7.4: "said 0.6-0.7 on 140 days, happened on
64%"), read from a committed G4 score report, never recomputed. History (`close_proxy`, the back-fill) and live
(`live_1500_proxy`) are reported apart, as G4 scores them: the back-fill was made after the fact from end-of-day data,
so it is not a live record."""

from __future__ import annotations

from ..forecast_scoring.score_inputs import CLOSE_PROXY, LIVE
from ..forecast_scoring.scores import calibration_bin

BIN_LINE = "said {low:.1f}-{high:.1f} on {count} days, happened on {share}, mean Brier {brier} over {scored}"
BACKFILL = "back-fill, not live: {record}"
LIVE_LINE = "live: {record}"
NO_BIN = "no calibration bin for this probability in the report ({scored} scored)"
NOT_ENOUGH = "not enough data yet ({scored} scored)"
NO_REPORT = "track record: no score report yet"


def _percent(share: float | None) -> str:
    return "n/a" if share is None else f"{share:.0%}"


def _number(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


class TrackRecords:
    """The score report's records by input mode, forecaster and question."""

    def __init__(self, report: dict | None):
        self.report = report
        self._scores = {
            (mode["mode"], s["forecaster"], s["question"]): s["primary"]
            for mode in (report or {}).get("modes", [])
            for s in mode["scores"]
        }

    def line(self, forecaster: str, question: str, probability: float) -> str:
        if self.report is None:
            return NO_REPORT
        backfill = self._record(CLOSE_PROXY, forecaster, question, probability)
        live = self._record(LIVE, forecaster, question, probability)
        return f"{BACKFILL.format(record=backfill)}; {LIVE_LINE.format(record=live)}"

    def _record(self, mode: str, forecaster: str, question: str, probability: float) -> str:
        primary = self._scores.get((mode, forecaster, question))
        scored = primary["scored"] if primary else 0
        if not scored:
            return NOT_ENOUGH.format(scored=scored)
        found = _bin(primary["calibration"], probability)
        if found is None:
            return NO_BIN.format(scored=scored)
        return BIN_LINE.format(
            low=found["low"], high=found["high"], count=found["count"], share=_percent(found["observed_frequency"]),
            brier=_number(primary["mean_brier"]), scored=scored,
        )  # fmt: skip


def _bin(calibration: list[dict], probability: float) -> dict | None:
    """The bin G4 itself put this probability in (`calibration_bin`), or None when the report has no such bin."""
    index = calibration_bin(probability)
    return calibration[index] if 0 <= probability <= 1 and index < len(calibration) else None
