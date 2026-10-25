"""The "no decision (late)" record (story E3 criterion 1): a book without a decision committed by the deadline gets
`journal/<book>/decisions/<date>/no_decision.json`, written once, and cannot join later. It sits beside D3's run
folders (D3 reads folders only), so scorecards see the missed day."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from ..constants import NO_DECISION_LATE
from ..playbook.decision_store import DecisionStore

FILE = "no_decision.json"


def write_no_decision(root: Path, book: str, day: date, deadline: datetime, reason: str) -> Path:
    path = DecisionStore(root, book).day_folder(day) / FILE
    body = {"kind": NO_DECISION_LATE, "book": book, "day": day.isoformat(), "deadline": deadline.isoformat(),
            "reason": reason}  # fmt: skip
    data = json.dumps(body, sort_keys=True, indent=1) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != data:
            raise FileExistsError(f"{path} already holds a different record: it is written once")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    return path
