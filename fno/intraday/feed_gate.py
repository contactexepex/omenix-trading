"""The go/no-go gate of the A16h probe's `alongside` run (judge 499): it runs only if that day's `coverage` run left
A16's 10:30 and 10:45 marks clean, read from A16's own ledger: status good, no failure, all expected quotes in."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ..constants_operations import STEP_OK
from .status import GOOD

GATE_MARKS = ("10:30", "10:45")
NOT_CLEAN = "no alongside today: A16's {mark} mark is not clean ({why})"


def alongside_gate(rows: Callable[[date], list[dict]], day: date) -> str:
    """'' when both marks are clean; else the one line that says why there is no alongside run that day."""
    by_mark = {row["mark_ist"]: row for row in rows(day)}
    for mark in GATE_MARKS:
        row = by_mark.get(mark)
        why = _problem(row)
        if why:
            return NOT_CLEAN.format(mark=mark, why=why)
    return ""


def _problem(row: dict | None) -> str:
    if row is None:
        return "no ledger row"
    if row["status"] != GOOD:
        return f"status {row['status']}"
    if row["failures"]:
        return "failures recorded"
    if row["recorded_contracts"] != row["expected_contracts"]:
        return "quotes missing"
    return ""


CANDLE_STEP = "candles"  # A16b's catch-up step in the daily run log (fno/constants_operations.py)
NO_CATCH_UP = "no ramp today: A16b's candle catch-up is not recorded done in journal/runs/{day}.json ({why})"


def catch_up_gate(run_log: dict | None, day: date) -> str:
    """'' once that day's A16b candle catch-up has finished (judge 499 addendum 2: it uses the same Groww key from
    15:33); else the one line that says why there is no after-close ramp."""
    if run_log is None:
        return NO_CATCH_UP.format(day=day, why="no run log")
    step = (run_log.get("steps") or {}).get(CANDLE_STEP)
    if not step:
        return NO_CATCH_UP.format(day=day, why="no candles step")
    if not step.get("finished_at"):
        return NO_CATCH_UP.format(day=day, why="the candles step has not finished")
    status = (step.get("result") or {}).get("status")
    if status != STEP_OK:  # a failed catch-up may be run again the same day, on the same key (judge 499 addendum 6)
        return NO_CATCH_UP.format(day=day, why=f"the candles step ended {status or 'without a status'}")
    return ""
