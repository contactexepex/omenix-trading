"""Each AI book's decision day as one committed record (story F1t): `journal/ai_decisions/<YYYY>/<d>_<book>_outcome
.json`, written once. It says what happened (the status and its reason), what the book was given (version, both pack
hashes, the cards item's hash, the units consulted), when its files were first seen on the remote, the D3 run when
promoted, and what a refusal restored. A rerun finds it and changes nothing."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .outcome import DayOutcome
from .paths import outcome_path
from .promote import Promotion

ALREADY = "already recorded"


class OutcomeRecords:
    def __init__(self, root: Path):
        self.root = Path(root)

    def exists(self, day: date, book: str) -> bool:
        return (self.root / outcome_path(day, book)).is_file()

    def read(self, day: date, book: str) -> dict:
        return json.loads((self.root / outcome_path(day, book)).read_text(encoding="utf-8"))

    def write(self, day: date, outcome: DayOutcome, labels: dict, consulted: tuple[str, ...],
              promotion: Promotion | None = None) -> Path:  # fmt: skip
        path = self.root / outcome_path(day, outcome.book)
        if path.is_file():
            return path
        record = {
            "book": outcome.book, "day": day.isoformat(), "status": outcome.status, "reason": outcome.reason,
            "version": outcome.version, "labels": labels, "consulted_units": list(consulted),
            "model_reported": outcome.model_reported, "model_configured": outcome.model_configured,
            "model_source": outcome.model_source, "model_check": outcome.model_check,
            "strategy_label": outcome.strategy_label,
            "commitment_commit": outcome.commitment_commit, "reveal_commit": outcome.reveal_commit,
            "received": {k: v.isoformat() if v else None for k, v in sorted(outcome.received.items())},
            "run_id": promotion.run_id if promotion else "",
            "restored": list(promotion.restored) if promotion else [],
            "refused_run": promotion.refused_run if promotion else {},
        }  # fmt: skip
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, sort_keys=True, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return path
