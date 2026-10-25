"""The v4 slot registrations (protocol section 5.6; the freeze plan, response 287): one committed row per family slot,
`research/forecasts/v4_slots.csv`, read by G8's scoring and the look's reconciliation. The freeze commit writes the
first rows; a later registration (V1's when it starts, the AI books' when they go live) is an appended row, written
before its slot's first counted forecast.

Refused, never read past (judge 184's note; ChatGPT review 119):
- a question outside the registered family or a slot outside `rules`, `hybrid`, `ai_team`;
- a second row for a slot (the first registered version is the member; a later variant is reported, never a member);
- `registered_on` after `effective_start` (a slot cannot be declared after the day its misses start);
- `effective_start` on or before the freeze's day (protocol section 4: a session after the freeze; judge 430 note 2);
- `effective_start` after the slot's first eligible session (its primary baseline's first live value after the
  freeze): a later start would hide the misses of the days between."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from datetime import date
from pathlib import Path

from ...constants import V4_SLOTS
from ...forecast_v4.terms import FAMILY_QUESTIONS
from .records import Registration, SlotRegistry

COLUMNS = ("question", "slot", "forecaster", "effective_start", "registered_on", "decision")


class RegistrationRefused(ValueError):
    """A slot registration that would change who is a member or hide misses; the report and the look stop."""


class SlotFile(SlotRegistry):
    def __init__(
        self,
        file: Path,
        first_eligible: Callable[[str], date | None],
        frozen_on: Callable[[], date | None] = lambda: None,
    ):
        """`first_eligible(question)`: the first live session after the freeze with a primary-baseline value, or
        None while there is none yet. `frozen_on()`: the freeze's day, None before the freeze."""
        self.file, self.first_eligible, self.frozen_on = Path(file), first_eligible, frozen_on

    def registered(self) -> dict[tuple[str, str], Registration]:
        if not self.file.exists():
            return {}
        found: dict[tuple[str, str], Registration] = {}
        for row in csv.DictReader(io.StringIO(self.file.read_text(encoding="utf-8"))):
            key, registration = self._checked(row)
            if key in found:
                raise RegistrationRefused(f"{key[0]}/{key[1]}: a second registration (the first one is the member)")
            found[key] = registration
        return found

    def _checked(self, row: dict) -> tuple[tuple[str, str], Registration]:
        question, slot = row["question"], row["slot"]
        if question not in FAMILY_QUESTIONS or slot not in V4_SLOTS:
            raise RegistrationRefused(f"{question}/{slot}: not a slot of v4's registered family")
        start, written = date.fromisoformat(row["effective_start"]), date.fromisoformat(row["registered_on"])
        if written > start:
            raise RegistrationRefused(f"{question}/{slot}: registered on {written}, after its effective start {start}")
        frozen = self.frozen_on()
        if frozen is not None and start <= frozen:
            raise RegistrationRefused(f"{question}/{slot}: effective start {start} is not after the freeze ({frozen})")
        eligible = self.first_eligible(question)
        if eligible is not None and start > eligible:
            raise RegistrationRefused(
                f"{question}/{slot}: effective start {start} is after the first eligible session {eligible}"
            )
        return (question, slot), Registration(row["forecaster"], start)
