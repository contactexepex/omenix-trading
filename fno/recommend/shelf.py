"""The recommender's pushed receipts in the repository (stories REC1c and REC1d): which days hold a recommendation and
which check files each day has. Read from the receipts only, so a file on Drive without its receipt is never seen."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..storage.receipts import RECEIPT_SUFFIX
from .store import AREA_FOLDER

CHECK_NAME = "{day}.check.{on}.json"
JSON_RECEIPT = f".json{RECEIPT_SUFFIX}"


def check_path(day: date, on: date) -> str:
    """The data-area path of the check of `day` made on `on`."""
    return f"{AREA_FOLDER}/{day:%Y}/{day:%m}/{CHECK_NAME.format(day=day.isoformat(), on=on.isoformat())}"


class ReceiptShelf:
    def __init__(self, receipts: Path):
        """`receipts`: the repository's receipts folder of the data area (`receipts/data`)."""
        self.receipts = receipts

    def recorded_days(self, upto: date) -> list[date]:
        """Every receipted recommendation up to `upto`, however old, oldest first."""
        names = (p.name.removesuffix(JSON_RECEIPT) for p in (self.receipts / AREA_FOLDER).rglob(f"*{JSON_RECEIPT}"))
        return sorted(d for d in (_day_of(name) for name in names) if d is not None and d <= upto)

    def checks(self, day: date, upto: date) -> list[date]:
        """The days `day` was checked on, up to `upto`, oldest first (a catch-up sees only what existed then)."""
        folder = self.receipts / AREA_FOLDER / f"{day:%Y}" / f"{day:%m}"
        found = (_checked_on(f.name) for f in folder.glob(f"{day.isoformat()}.check.*{JSON_RECEIPT}"))
        return sorted(on for on in found if on <= upto)


def _checked_on(receipt_name: str) -> date:
    """The check day in `<day>.check.<on>.json.sha256`."""
    return date.fromisoformat(receipt_name.removesuffix(JSON_RECEIPT).rsplit(".", 1)[-1])


def _day_of(name: str) -> date | None:
    """`2026-11-02` names a recommendation; a check's receipt (`<day>.check.<on>`) names none."""
    try:
        return date.fromisoformat(name)
    except ValueError:
        return None
