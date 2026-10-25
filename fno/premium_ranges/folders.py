"""G13d's paths in Drive's `data` area (O9) and its receipts in the checkout; O1's steps commit only these."""

from __future__ import annotations

from datetime import date, datetime

DATA_AREA, RECEIPTS_ROOT = "data", "receipts"
ROOT = "premium_ranges/v1"
LIVE, SEALS, SCORES = f"{ROOT}/live", f"{ROOT}/seals", f"{ROOT}/scores"


def live_path(underlying: str, day: date, issue: str) -> str:
    return f"{LIVE}/{day:%Y}/{day:%m}/{underlying.lower()}_{day.isoformat()}_{issue}.json"


def seal_path(underlying: str, day: date, issue: str) -> str:
    return f"{SEALS}/{day:%Y}/{day:%m}/{underlying.lower()}_{day.isoformat()}_{issue}.json"


def scores_path(made: datetime, content: str) -> str:
    return f"{SCORES}/{made:%Y-%m-%dT%H%M%S}_{content[:12]}.json"


def receipt_file(path: str) -> str:
    """The repository path of a G13d Drive file's receipt (O9: `receipts/<drive path>.sha256`)."""
    return f"{RECEIPTS_ROOT}/{DATA_AREA}/{path}.sha256"


def receipt_pathspecs() -> tuple[str, ...]:
    return (f"{RECEIPTS_ROOT}/{DATA_AREA}/{ROOT}/",)
