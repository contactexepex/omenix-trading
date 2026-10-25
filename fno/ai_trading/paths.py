"""Where the AI books' trading records live (story F1t). None of them is inside a book's own folder, so none enters a
private pack: each day's fire log, each book's submissions (commitment and reveal), its outcome record and its audits
are under `journal/ai_decisions/`, through `fno/ai/paths.py`'s own functions with this folder (one shape for every AI
run, G11's `RunTerms`). The run's timing sits beside the forecasts' timing files, which BG1's recorder reads. The
routine's working files and the remote observer's readings are git-ignored. Standard library only."""

from __future__ import annotations

from datetime import date

from ..ai import paths as ai_paths

DECISIONS_FOLDER = "journal/ai_decisions"
DECISION_RUN = "decision"  # the run's name: its protocol in `RunTerms`, its timing file and its usage role
WORK_FOLDER = ".ai_decision"  # the routine's private working files (salt, pointer); never committed
OBSERVATIONS_FOLDER = ".ai_decision_observations"  # the remote observer's readings (daily run side); never committed


def fired_path(day: date) -> str:
    return ai_paths.fired_path(day, DECISIONS_FOLDER)


def commitment_path(day: date, book: str) -> str:
    return ai_paths.commitment_path(day, book, DECISIONS_FOLDER)


def reveal_path(day: date, book: str) -> str:
    return ai_paths.reveal_path(day, book, DECISIONS_FOLDER)


def transcript_audit_path(day: date, book: str) -> str:
    return ai_paths.transcript_audit_path(day, book, DECISIONS_FOLDER)


def outcome_path(day: date, book: str) -> str:
    return f"{DECISIONS_FOLDER}/{day:%Y}/{day.isoformat()}_{book}_outcome.json"


def model_audit_path(day: date, book: str) -> str:
    """The transcript's check of the reported model fields (criterion 3c), beside the transcript audit."""
    return f"{DECISIONS_FOLDER}/{day:%Y}/{day.isoformat()}_{book}_model_audit.json"


def timing_path(day: date, book: str) -> str:
    """The decision run's own timing (F8c's mechanism), named apart from the book's forecast run."""
    return f"{ai_paths.AI_FOLDER}/timing/{day:%Y}/{day.isoformat()}_{book}_{DECISION_RUN}.timing.json"


def observations_path(day: date) -> str:
    return f"{OBSERVATIONS_FOLDER}/{day.isoformat()}.json"


def common_pack_path(day: date) -> str:
    """E2's committed common pack (`fno/desk/pack_store.py`), repeated here because the routine side cannot import the
    desk's pack code; `tests/ai_trading/test_paths.py` keeps them equal."""
    return f"journal/packs/{day.isoformat()}/common.json"


def judge_path(day: date, book: str) -> str:
    """The daily judge's verdict file (F4 design 3; `NoJudge`'s until F4 lands)."""
    return f"{DECISIONS_FOLDER}/{day:%Y}/{day.isoformat()}_{book}_judge.json"
