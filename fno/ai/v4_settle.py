"""Story G11, the AI books' v4 rows from their settled days (design item 5, criterion 6): every collected v4 book-day
whose scoring gate has settled becomes its rows (`v4_rows.write_book_day`, written once; a day already written adds
nothing), and every day still pending is counted: "N days awaiting audit". Run after each collection, so a day whose
audit lands later gets its rows on the next run, and G8 recomputes its reports from the files.

Everything a row carries comes from the audit file the collection wrote once (the outcome, the fire entry, the
collection time and the release record's SHA), so a re-run writes the same rows."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..forecast_v4_rules.records import RecordConflict
from .draw_seed import Week, WeekSeed
from .paths import TRANSCRIPT_AUDIT_SUFFIX
from .run_terms import V4_TERMS
from .scoring_gate import PENDING, scoring_status
from .v4_rows import BookDay, write_book_day
from .versions import version_by_label

AUDITS = "*/*_audit.json"  # the collection's audits; the transcript audits share the folder (round 2c) and are skipped
LINE = "Omenix F&O AI forecasts v4: {result}"


@dataclass
class V4RowSettler:
    root: Path
    records_folder: Path  # G8's folder: research/forecasts/v4
    seeds: Callable[[], dict[Week, WeekSeed]]  # the weekly audit draws' verified seeds

    def settle(self) -> list[str]:
        files = _collection_audits(self.root / V4_TERMS.folder)
        seeds = self.seeds() if files else {}  # the draws' seeds read the Drive archive: only when there is a day
        added, waiting, problems = 0, [], []
        for file in files:
            try:
                rows, pending = self._settle(file, seeds)
            except (KeyError, ValueError, RecordConflict) as broken:  # one bad day is said, never stops the others
                problems.append(f"{file.name}: {type(broken).__name__}: {broken}")
                continue
            added += rows
            waiting += [pending] if pending else []
        lines = [LINE.format(result=f"{added} v4 row(s) added; {len(waiting)} day(s) awaiting audit")]
        lines += [LINE.format(result=f"awaiting audit: {entry}") for entry in waiting]
        return lines + [LINE.format(result=f"NOT settled, fix and rerun: {entry}") for entry in problems]

    def _settle(self, file: Path, seeds: dict[Week, WeekSeed]) -> tuple[int, str]:
        """The rows one audit adds, or the day it leaves waiting."""
        audit = json.loads(file.read_text(encoding="utf-8"))
        day = date.fromisoformat(audit["day"])
        gate = scoring_status(self.root, day, audit["book"], seeds, V4_TERMS)
        if gate.status == PENDING:
            return 0, f"{day} {audit['book']} ({gate.reason})"
        book_day = _book_day(audit, day, gate)
        return write_book_day(self.records_folder, book_day, audit["fire"]["questions"], audit["released_sha256"]), ""


def _collection_audits(folder: Path) -> list[Path]:
    return sorted(f for f in folder.glob(AUDITS) if not f.name.endswith(TRANSCRIPT_AUDIT_SUFFIX))


def _book_day(audit: dict, day: date, gate) -> BookDay:
    fire = audit["fire"]
    return BookDay(version_by_label(audit["version"]), day, gate, bool(fire.get("stop_rule")), audit["counted"],
                   fire.get("input_sha256", ""), audit["collected_at"], fire.get("pack_sha256", ""))  # fmt: skip
