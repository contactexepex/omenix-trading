"""The 14:30 overlap watch (story G10 completion, criterion 11; judge 580 finding 2): the `v4` capture and A16's 14:30
mark use the same Groww account in the same minute. At the day's end, one #fno-desk line when either shows any
failure: the `v4` attempts' failure count and the canonical attempt's recorded of expected contracts, A16's 14:30 row
status and failures; counts and status words only, never a quote value. A day with no `v4` capture (not live) says
nothing; a clean day says nothing; A16's row missing (its routine did not run) is named apart from a clash."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, time
from pathlib import Path

from ..intraday.ledger import FILE_NAME
from ..intraday.status import GOOD
from ..models import IST
from ..quotes.v4_extras import NO_MONTHLY, RECORDED

A16_MARK = time(14, 30)
LINE = "v4 14:30 overlap {day}: v4 capture {v4}; A16's 14:30 mark {a16} (Groww's messages are withheld: see the counts)"
V4_PART = "{failures} failure(s) in {attempts} attempt(s), {recorded} of {expected} contracts in the canonical one"
A16_ROW = "{status}, failures: {failures}"
A16_MISSING = "missing (no row: A16's routine did not record it)"


class OverlapWatch:
    def __init__(self, v4_folder: Path, intraday_folder: Path):
        """`v4_folder`: the v4 dataset's sidecar folder; `intraday_folder`: A16's folder holding `slots/` (both in the
        checkout)."""
        self.v4_folder, self.intraday_folder = Path(v4_folder), Path(intraday_folder)

    def line(self, day: date) -> str | None:
        attempts = self._attempts(day)
        if not attempts:
            return None
        failures = sum(_failures(meta) for meta in attempts.values())
        row = self._a16_row(day)
        if failures == 0 and row is not None and row["status"] == GOOD and not row["failures"]:
            return None
        canonical = attempts.get(self._canonical(day), {})
        v4 = V4_PART.format(failures=failures, attempts=len(attempts), recorded=canonical.get("recorded_contracts", 0),
                            expected=canonical.get("expected_contracts", 0))  # fmt: skip
        a16 = A16_MISSING if row is None else A16_ROW.format(status=row["status"], failures=row["failures"] or "none")
        return LINE.format(day=day, v4=v4, a16=a16)

    def _attempts(self, day: date) -> dict[str, dict]:
        folder = self.v4_folder / f"{day:%Y}" / f"{day:%m}"
        files = sorted(folder.glob(f"nifty_{day:%Y%m%d}_*.meta.json"))
        return {f.name.removesuffix(".meta.json"): json.loads(f.read_text(encoding="utf-8")) for f in files}

    def _canonical(self, day: date) -> str:
        marker = self.v4_folder / f"{day:%Y}" / f"{day:%m}" / f"nifty_{day:%Y%m%d}.canonical"
        return marker.read_text(encoding="utf-8").strip() if marker.is_file() else ""

    def _a16_row(self, day: date) -> dict | None:
        mark = datetime.combine(day, A16_MARK, IST)
        file = self.intraday_folder / FILE_NAME.format(day=day, mark=mark)
        if not file.is_file():
            return None
        with file.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return rows[-1] if rows else None


def _failures(meta: dict) -> int:
    """Every failed request of one attempt: A4's own, the extras' V4 expiry quotes and a future quote that did not come
    (judge 584 SF1: the extras' requests are sent in the same minute as A16's mark)."""
    future = meta.get("future_quote")
    future_failed = future is not None and future not in (RECORDED, NO_MONTHLY)
    return len(meta.get("failures") or []) + len(meta.get("v4_failures") or []) + int(future_failed)
