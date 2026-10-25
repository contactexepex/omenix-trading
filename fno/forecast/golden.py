"""Golden values of the inputs the forecast protocol computes at the forecast date (judge 47): IV30 (value, flag,
expiries) and trailing 20-day RV for every panel trading day, so the protocol freezes behaviour, not library bytes.

A refactor of the shared code (B1's IV and RV, the calendar reader) that keeps every number passes; a change to any
number fails `tests/forecast/test_golden.py` and needs a new protocol version, unless a panel revision (story A11)
changed that day's inputs, which the change must name. Outcomes are not here: they would read the future.
"""

from __future__ import annotations

import csv
import io
import math
from collections.abc import Iterable, Sequence

from ..constants import SESSION_MUHURAT
from ..research_data.calendar import SessionCalendar
from ..research_data.panel_reader import NiftyPanel
from .iv30 import PanelAtmIv30
from .targets import ForecastTargets, daily_closes

GOLDEN_FILE = "research/forecasts/golden_iv30_rv20.csv"
GOLDEN_COLUMNS = ("date", "iv30_points", "iv30_flagged", "iv30_expiries", "trailing_rv20_points")
TOLERANCE = 1e-12  # points; the same code gives the same floats, so any real change is far larger


def _number(value: float | None) -> str:
    return "" if value is None else repr(float(value))


def golden_rows(panel: NiftyPanel, calendar: SessionCalendar, estimator: PanelAtmIv30) -> list[dict[str, str]]:
    """One row per trading day of the panel that has option rows (the warm-up sessions give earlier closes only)."""
    days = sorted(day for day in panel.options if calendar.session_kind(day) != SESSION_MUHURAT)
    if not days:
        return []
    closes = daily_closes(calendar, panel.sessions[0].day, days[-1], panel.sessions)
    targets, rows = ForecastTargets(closes), []
    for day in days:
        iv30 = estimator.estimate(panel, day)
        rows.append({
            "date": day.isoformat(),
            "iv30_points": _number(iv30.points if iv30 else None),
            "iv30_flagged": "" if iv30 is None else str(iv30.flagged).lower(),
            "iv30_expiries": "" if iv30 is None else ";".join(e.isoformat() for e in iv30.expiries),
            "trailing_rv20_points": _number(targets.trailing_rv(day)),
        })  # fmt: skip
    return rows


def write_golden(rows: Iterable[dict[str, str]]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=GOLDEN_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def read_golden(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != GOLDEN_COLUMNS:
        raise ValueError(f"golden file columns must be {GOLDEN_COLUMNS}")
    return list(reader)


def _same_number(expected: str, actual: str) -> bool:
    if expected == "" or actual == "":
        return expected == actual
    return math.isclose(float(expected), float(actual), rel_tol=0.0, abs_tol=TOLERANCE)


def differences(expected: Sequence[dict[str, str]], actual: Sequence[dict[str, str]]) -> list[str]:
    """Every day whose recomputed values differ from the golden ones (and days added or missing)."""
    want, got = {r["date"]: r for r in expected}, {r["date"]: r for r in actual}
    problems = [f"{day}: missing from the recomputation" for day in sorted(set(want) - set(got))]
    problems += [f"{day}: not in the golden file" for day in sorted(set(got) - set(want))]
    for day in sorted(set(want) & set(got)):
        w, g = want[day], got[day]
        numbers = all(_same_number(w[c], g[c]) for c in ("iv30_points", "trailing_rv20_points"))
        if not numbers or w["iv30_flagged"] != g["iv30_flagged"] or w["iv30_expiries"] != g["iv30_expiries"]:
            problems.append(f"{day}: golden {dict(w)} but now {dict(g)}")
    return problems
