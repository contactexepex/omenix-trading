"""Story G11 C13, the AI books' 10 slot registrations (`hybrid` and `ai_team` on each of the five family questions),
appended to `research/forecasts/v4_slots.csv` in the protocol's order:

1. `FREEZE_v4.md` and the rules rows exist (the freeze builder's; owner, 21 Oct 2026, "v4 freeze answers" (3));
2. these rows, each `effective_start` = the first scored session after the freeze's day, never after any slot's first
   eligible session (`slot_file.py` refuses a later start for the whole file, which would stop every v4 score), with
   `registered_on` = the day written, before that session opens (09:15 IST);
3. `daily.live_from.ai_books_v4` set by the owner to that same session; a later go-live leaves `not_fired` misses.

Refused, writing nothing: before the freeze, with no rules row at all, once a new row's first session has begun, a
file that already holds another AI forecaster for a slot, or a result `SlotFile` itself refuses. A question whose rules
row is not there yet waits and is named; the command adds its rows when run again after that row lands. `--print`
gives the rows for the freeze commit instead of writing them, the safe way to land them on the freeze's own day."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from ..constants import AI_BOOKS, V4_SLOT_RULES
from ..forecast_scoring.v4.records import LookRecords, SlotRegistry
from ..forecast_scoring.v4.slot_file import COLUMNS, RegistrationRefused
from ..forecast_v4.terms import FAMILY_QUESTIONS
from ..models import IST
from .run_terms import FORECAST_PROTOCOL_V4
from .v4_rows import SLOTS
from .versions import current_version

DECISION = "DESK_DECISIONS 21 Oct 2026 v4 freeze answers (3); 24 Oct 2026 Close v4 in full first"
SESSION_OPENS = time(9, 15)
LINE = "Omenix F&O AI v4 slots: {result}"
LOOK_AHEAD_DAYS = 15  # the first scored session after the freeze is found within this many calendar days


class RegisterRefused(ValueError):
    """The registration would break the protocol's order or the slot file; nothing is written."""


@dataclass
class SlotRegistrar:
    slots_file: Path
    looks: LookRecords
    slots: Callable[[], SlotRegistry]  # G8's reading of `slots_file` (its own freeze and eligibility checks)
    sessions: Callable[[date, date], list[date]]  # v4's scored sessions from the first day to the last
    clock: Callable[[], datetime]

    def rows(self) -> tuple[list[dict], list[str]]:
        """The AI rows still to write, and the questions that wait for their rules row. Each question's rows start on
        the later of the first session after the freeze and its rules row's own start; a question already registered
        with the same forecasters adds nothing; with another it is refused (the first registration is the member)."""
        if not self.looks.frozen():
            raise RegisterRefused("FREEZE_v4.md does not exist: the AI slots are registered after the freeze")
        registered = self.slots().registered()
        first, now = self._first_session_after(self.looks.frozen_on()), self.clock().astimezone(IST)
        forecaster = {book: current_version(book, FORECAST_PROTOCOL_V4).forecaster for book in AI_BOOKS}
        rows, waiting = [], []
        for question in FAMILY_QUESTIONS:
            rule = registered.get((question, V4_SLOT_RULES))
            if rule is None:
                waiting.append(question)
                continue
            new = [b for b in AI_BOOKS if self._new(registered, question, b, forecaster[b])]
            start = max(first, rule.effective_start)
            if new and now >= datetime.combine(start, SESSION_OPENS, IST):
                raise RegisterRefused(f"{question}'s first session {start} has begun: a row must be written before it")
            rows += [{"question": question, "slot": SLOTS[b], "forecaster": forecaster[b],
                      "effective_start": f"{start}", "registered_on": now.date().isoformat(), "decision": DECISION}
                     for b in new]  # fmt: skip
        if len(waiting) == len(FAMILY_QUESTIONS):
            raise RegisterRefused("no rules row yet: the freeze's rules rows come first")
        return rows, waiting

    @staticmethod
    def _new(registered: dict, question: str, book: str, forecaster: str) -> bool:
        found = registered.get((question, SLOTS[book]))
        if found is not None and found.forecaster != forecaster:
            raise RegisterRefused(f"{question}/{SLOTS[book]} is registered to {found.forecaster} (the member)")
        return found is None

    def register(self, write: bool) -> list[str]:
        try:
            rows, waiting = self.rows()
            lines = self._append(rows) if write else [_text(rows, header=False).rstrip("\n")]
        except (RegisterRefused, RegistrationRefused) as refused:
            return [LINE.format(result=f"refused, nothing written: {refused}")]
        return lines + ([LINE.format(result=f"waiting for their rules row: {', '.join(waiting)}")] if waiting else [])

    def _append(self, rows: list[dict]) -> list[str]:
        if not rows:
            return [LINE.format(result="already registered (nothing to add)")]
        before = self.slots_file.read_text(encoding="utf-8") if self.slots_file.is_file() else ""
        self.slots_file.write_text(before + _text(rows, header=not before), encoding="utf-8")
        try:
            self.slots().registered()  # G8's own reading of the result
        except RegistrationRefused:
            self._restore(before)
            raise
        starts = ", ".join(sorted({r["effective_start"] for r in rows}))
        return [LINE.format(result=f"{len(rows)} rows registered, effective {starts}: {self.slots_file.name}")]

    def _restore(self, before: str) -> None:
        if before:
            self.slots_file.write_text(before, encoding="utf-8")
        else:
            self.slots_file.unlink()

    def _first_session_after(self, day: date) -> date:
        found = self.sessions(day + timedelta(days=1), day + timedelta(days=LOOK_AHEAD_DAYS))
        if not found:
            raise RegisterRefused(f"no scored session within {LOOK_AHEAD_DAYS} days after {day}")
        return found[0]


def _text(rows: list[dict], header: bool) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    if header:
        writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()
