"""Where the AI books' inputs and outputs live in the repository (stories F1 and G5).

The v2 pack folder and the closes file are the same paths the frozen capture uses (`fno/forecast/capture.py`,
`fno/forecast/baseline_wiring.py`); they are repeated here because importing those modules pulls in libraries a
routine would first have to install. `tests/ai/test_paths.py` keeps them equal."""

from __future__ import annotations

from datetime import date

LIVE_PACK_FOLDER = "research/forecasts/live_v2"  # the v2 pack and Book 1's records, written by forecast-capture
CLOSES_FILE = "research/data/nifty-panel/warmup_closes.csv"  # official closes, extended each evening (story O6)
AI_FOLDER = "research/forecasts/ai_v1"  # the AI books' records, audit files and submissions
WORK_FOLDER = ".ai_book"  # the routine's private working files (salt, export); never committed


def pack_path(day: date) -> str:
    return f"{LIVE_PACK_FOLDER}/{day:%Y}/{day.isoformat()}_pack.json"


def rules_path(day: date) -> str:
    return f"{LIVE_PACK_FOLDER}/{day:%Y}/{day.isoformat()}_forecasts.csv"


def commitment_path(day: date, book: str, folder: str = AI_FOLDER) -> str:
    return f"{folder}/submissions/{day:%Y}/{day.isoformat()}_{book}.commitment.json"


def reveal_path(day: date, book: str, folder: str = AI_FOLDER) -> str:
    return f"{folder}/submissions/{day:%Y}/{day.isoformat()}_{book}.reveal.json"


def records_path(day: date, book: str) -> str:
    return f"{AI_FOLDER}/{day:%Y}/{day.isoformat()}_{book}_forecasts.csv"


def audit_path(day: date, book: str, folder: str = AI_FOLDER) -> str:
    return f"{folder}/{day:%Y}/{day.isoformat()}_{book}_audit.json"


def fired_path(day: date, folder: str = AI_FOLDER) -> str:
    return f"{folder}/{day:%Y}/{day.isoformat()}_fired.json"


def timing_path(day: date, book: str) -> str:
    """The run's own timing (BG1's self-timed record, story F8c), published by `reveal`."""
    return f"{AI_FOLDER}/timing/{day:%Y}/{day.isoformat()}_{book}.timing.json"


TRANSCRIPT_AUDIT_SUFFIX = "_transcript_audit.json"


def transcript_audit_path(day: date, book: str, folder: str = AI_FOLDER) -> str:
    return f"{folder}/{day:%Y}/{day.isoformat()}_{book}{TRANSCRIPT_AUDIT_SUFFIX}"


AI_V4_FOLDER = "research/forecasts/ai_v4"  # the AI books' v4 fire logs and submissions (their rows: v4/<forecaster>/)
