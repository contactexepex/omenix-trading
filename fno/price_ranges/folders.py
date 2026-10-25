"""G13b's paths in Drive's `data` area and its receipts in the checkout (parts A3, A4, A6); O1's step commits only
these receipts."""

from __future__ import annotations

from datetime import date, datetime

DATA_AREA = "data"  # O9's area
RECEIPTS_ROOT = "receipts"  # O9's receipts tree in the checkout
ROOT = "price_ranges/v1"
LIVE, BACKFILL, SCORES, CLOSES = f"{ROOT}/live", f"{ROOT}/backfill", f"{ROOT}/scores", f"{ROOT}/closes"
SEALS = f"{ROOT}/seals"


def live_path(underlying: str, day: date, issue: str) -> str:
    return f"{LIVE}/{day:%Y}/{day:%m}/{underlying.lower()}_{day.isoformat()}_{issue}.json"


def seal_path(underlying: str, day: date, issue: str) -> str:
    return f"{SEALS}/{day:%Y}/{day:%m}/{underlying.lower()}_{day.isoformat()}_{issue}.json"


def backfill_path(label: str, method: str, underlying: str, first: date, last: date, content: str) -> str:
    name = f"{underlying.lower()}_{first.isoformat()}_{last.isoformat()}_{content[:12]}.json.gz"
    return f"{BACKFILL}/{label}_{method[:8]}/{name}"


def scores_path(made: datetime, content: str) -> str:
    """Named by the run's IST time, so the latest report sorts last even on a day with two runs."""
    return f"{SCORES}/{made:%Y-%m-%dT%H%M%S}_{content[:12]}.json"


def closes_path(underlying: str, through: date, rows: int, content: str) -> str:
    """Through date, then row count: a later update always sorts last, a late file's filled day included."""
    return f"{CLOSES}/{underlying.lower()}_through_{through.isoformat()}_rows{rows:06d}_{content[:12]}.csv"


def drive(path: str) -> str:
    return f"{DATA_AREA}/{path}"


def receipt_pathspecs() -> tuple[str, ...]:
    """The receipts of G13b's Drive files only (as G13's and M1's), never a shared folder."""
    return (f"{RECEIPTS_ROOT}/{DATA_AREA}/{ROOT}/",)
