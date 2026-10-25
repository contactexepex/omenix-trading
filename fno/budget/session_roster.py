"""Which development sessions exist, so the meter knows whether their usage is fully captured (judge 104 must-fix 3).
A Claude session saves `list_sessions(mine=true)` page by page into one JSON file outside the repository:
`{"captured_at": <ISO with zone>, "limit": <page size asked>, "pages": [{"after_id": <cursor, null first>,
"response": <list_sessions>}, ...]}`. Each page must be read with the previous page's `last_id`, and the last page must
hold fewer sessions than the limit (the end of the list). Only ids and times are kept, in
`accounting/ai_session_roster.csv`. Trigger-fired runs (the books, the data routines) are not listed by the tool: the
books are checked against the fire logs instead; the data routines are not checked (a stated limit)."""

from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from ..models import IST
from .usage_ledger import session_key
from .usage_reader import ExportRefused, ist_time, shaped

ROSTER_FILE = "accounting/ai_session_roster.csv"
MAX_LIMIT = 100  # list_sessions' largest page; the export's own limit cannot be checked further (a stated limit)
COLUMNS = ("session_id", "created_at", "updated_at", "captured_at")
BROKEN = "roster page {n} was not read with the previous page's last_id: a page is missing, so nothing is recorded"
NOT_THE_END = "the roster's last page is full ({n} of {limit}): more sessions may follow, so nothing is recorded"
STALE = "development not checked: no session roster read since {since}"
UNCAPTURED = "{n} development session(s) not fully captured"


def read_roster_export(path: Path) -> list[dict]:
    export = shaped(json.loads(path.read_text(encoding="utf-8")), dict, "the roster export")
    captured = ist_time(export.get("captured_at") or "", "captured_at").isoformat()
    limit, cursor, sessions = export.get("limit"), None, []
    if not isinstance(limit, int) or not 0 < limit <= MAX_LIMIT:
        raise ExportRefused(
            f"the roster's limit {limit!r} is not a page size from 1 to {MAX_LIMIT} (the tool's maximum)"
        )
    pages = export.get("pages") or []
    for n, page in enumerate(shaped(pages, list, "pages"), start=1):
        if shaped(page, dict, f"roster page {n}").get("after_id") != cursor:
            raise ExportRefused(BROKEN.format(n=n))
        response = (page.get("response") or {}).get("ccr", page.get("response") or {})
        sessions += response.get("data") or []
        cursor = response.get("last_id")
    last = ((pages[-1].get("response") or {}).get("ccr", pages[-1].get("response")) or {}) if pages else {}
    if not pages or limit <= 0 or len(last.get("data") or []) >= limit:
        raise ExportRefused(NOT_THE_END.format(n=len(last.get("data") or []), limit=limit))
    return [_row(s, captured) for s in sessions]


def _row(session: dict, captured: str) -> dict:
    times = {k: ist_time(session.get(k) or "", k).isoformat() for k in ("created_at", "updated_at")}
    return {"session_id": session.get("id") or "", **times, "captured_at": captured}


class SessionRoster:
    def __init__(self, root: Path):
        self._path = root / ROSTER_FILE

    def rows(self) -> list[dict]:
        if not self._path.is_file():
            return []
        reader = csv.DictReader(io.StringIO(self._path.read_text(encoding="utf-8")))
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f"{ROSTER_FILE} columns must be {COLUMNS}")
        rows = list(reader)
        for row in rows:  # a hand-edited time without its zone is refused here, not compared later
            for column in ("created_at", "updated_at", "captured_at"):
                ist_time(row[column] or "", f"{ROSTER_FILE} {row['session_id']} {column}")
        return rows

    def record(self, new: list[dict]) -> int:
        """Merges a reading: each session keeps its latest times. Returns the number of sessions now listed."""
        merged = {row["session_id"]: row for row in self.rows()}
        for row in new:
            old = merged.get(row["session_id"], row)
            merged[row["session_id"]] = {**row, "updated_at": max(old["updated_at"], row["updated_at"])}
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(merged.values(), key=lambda r: r["session_id"]))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".csv.tmp")
        temporary.write_text(out.getvalue(), encoding="utf-8")
        os.replace(temporary, self._path)
        return len(merged)


@dataclass(frozen=True)
class DevelopmentCoverage:
    complete: bool
    missing: tuple[str, ...]
    reason: str


def development_coverage(roster: list[dict], usage: list[dict], month: str, before: date) -> DevelopmentCoverage:
    """Complete when a roster was read after the last complete day and every session active in the month on those days
    has a usage reading complete past its last active day (or up to the last complete day)."""
    first = date.fromisoformat(month + "-01")
    next_month = date(first.year + first.month // 12, first.month % 12 + 1, 1)
    cutoff = _start(min(before, next_month))
    if not roster or max(datetime.fromisoformat(r["captured_at"]) for r in roster) < cutoff:
        return DevelopmentCoverage(False, (), STALE.format(since=cutoff.isoformat()))
    complete_to: dict[str, date] = {}  # per session: days before this are held in full
    for row in usage:
        key, upto = session_key(row["session_id"]), date.fromisoformat(row["complete_before"])
        complete_to[key] = max(complete_to.get(key, upto), upto)
    missing = tuple(
        r["session_id"]
        for r in roster
        if datetime.fromisoformat(r["created_at"]) < cutoff
        and datetime.fromisoformat(r["updated_at"]) >= _start(first)
        and complete_to.get(session_key(r["session_id"]), date.min) < _needed(r["updated_at"], cutoff.date())
    )
    return DevelopmentCoverage(not missing, missing, UNCAPTURED.format(n=len(missing)) if missing else "")


def _needed(updated_at: str, cutoff: date) -> date:
    """A reading must be complete past the session's last active day, or up to the cutoff if it is still active."""
    return min(datetime.fromisoformat(updated_at).date() + timedelta(days=1), cutoff)


def _start(day: date) -> datetime:
    return datetime.combine(day, time(0), IST)
