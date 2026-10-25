"""Story G11, the AI books' v4 rows: each book-day becomes one G7-schema row per started v4 question in G8's folder
(`research/forecasts/v4/<forecaster>/<question>.csv`, the forecaster being the registered version, e.g. `book3_ai_v2`:
protocol v4's slot holds the first version registered for it, so a later version can never pour rows into it), and
every failed run is a miss, never a gap.

- **The status is F1's gate, used as is** (`scoring_gate.scoring_status`, the one rule every AI reader calls): scored
  is `ok` with the book's value; an unscored day keeps its outcome's own name (late, not_fired, no_submission,
  not_revealed, invalid, model_mismatch, exposed); a transcript breach is `breach`; a day the stop rule kept from
  firing is `stopped`, read from the fire log's own flag (never from the reason's wording: R2/G7, 16 Oct). A pending
  day (audit due, week not drawn, not collected) gets **no row**: a written row never changes, so it waits, and G8's
  look refuses while any slot-day has none (the A16/G8 builder's reconciliation).
- **One row per started question,** the same list the rules slot answers that day (passed in, never an AI list).
- **The row** is G7's own (`records.record`, its range checks reused), with the book's registered version in
  `forecaster_version`, `label=live` (AI answers have no back-fill), `kind=ai`, the book's slot, the prompt's hash in
  `method_sha256` and the book's own inputs' hash in `inputs_sha256`. Written once (`records.write`).
- **The pack binding** (G10 part 2, judge 274 add. 1): before any row is written, the pack the book was given must be
  the released one (`fno/v4_pack.guard`); on a `system_late` day (none released) the book has no row. Every row
  then carries the release record's SHA in G7's `pack_sha256` column (G11 C9)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from ..constants import BOOK2_HYBRID, BOOK3_AI, V4_SLOT_AI, V4_SLOT_HYBRID
from ..forecast_v4_rules import records
from ..forecast_v4_rules.baselines import OK
from ..v4_pack.guard import check_pack_binding
from .outcome import EXPOSED, INVALID, LATE, MODEL_MISMATCH, NO_SUBMISSION, NOT_FIRED, NOT_REVEALED
from .scoring_gate import PENDING, SCORED, ScoringStatus
from .versions import BookVersion

AI_KIND = "ai"
SLOTS = {BOOK2_HYBRID: V4_SLOT_HYBRID, BOOK3_AI: V4_SLOT_AI}
BREACH, STOPPED = "breach", "stopped"
OUTCOME_MISSES = (LATE, NOT_FIRED, NO_SUBMISSION, NOT_REVEALED, INVALID, MODEL_MISMATCH, EXPOSED)
TRANSCRIPT_BREACH = "transcript breach"  # the gate's reason for a breach found by the transcript audit
UNKNOWN_OUTCOME = "{book} {day}: outcome {reason!r} has no v4 status; nothing is written (never a guessed status)"


@dataclass(frozen=True)
class BookDay:
    """What the collection settled for one book on one day: the registered version it ran (its book, forecaster,
    label and prompt hash all come from it, so the guard's book and the folder can never disagree), the gate's answer,
    whether the stop rule kept it from firing (the fire log's flag), the values the book revealed per question (None
    where it gave none), its own input's hash and the pack it was given."""

    registered: BookVersion
    day: date
    gate: ScoringStatus
    stop_rule: bool
    values: Mapping[str, float | None]
    inputs_sha256: str  # the book's own input (its pointer's)
    made_at: str
    pack_sha256: str  # the pack the book was given (its pointer's)

    @property
    def book(self) -> str:
        return self.registered.book

    @property
    def forecaster(self) -> str:
        """The slot's ledger name and record folder, e.g. book3_ai_v2."""
        return self.registered.forecaster


def v4_status(day: BookDay) -> str | None:
    """The day's v4 status, or None while its gate is pending (no row yet)."""
    gate = day.gate
    if gate.status == PENDING:
        return None
    if gate.status == SCORED:
        return OK
    if gate.reason.startswith(TRANSCRIPT_BREACH):
        return BREACH
    if gate.reason == NOT_FIRED and day.stop_rule:
        return STOPPED
    if gate.reason in OUTCOME_MISSES:
        return gate.reason
    raise ValueError(UNKNOWN_OUTCOME.format(book=day.book, day=day.day, reason=gate.reason))


def v4_rows(day: BookDay, questions: Sequence[str], pack_sha256: str = "") -> list[records.Record]:
    """One row per started question; empty while the gate is pending. A scored day without a value for a question is
    that question's `invalid` row (the book answered, but not this question). `pack_sha256`: the release record's."""
    status = v4_status(day)
    if status is None:
        return []
    audit = dict(label=records.LIVE, kind=AI_KIND, slot=SLOTS[day.book], method_sha256=day.registered.prompt_sha256,
                 inputs_sha256=day.inputs_sha256, made_at=day.made_at)  # fmt: skip
    rows = []
    for question in questions:
        value = day.values.get(question) if status == OK else None
        own = status if status != OK or value is not None else INVALID
        row = records.record(day.day, question, own, value, pack_sha256, **audit)
        rows.append(replace(row, forecaster_version=day.registered.label))
    return rows


def write_book_day(folder: Path, day: BookDay, questions: Sequence[str], released_sha256: str) -> int:
    """The day's rows written once in the book's own folder; the number added (0 while pending, or already written).
    `released_sha256`: the release record's pack (empty on a system_late day); another pack refuses every row."""
    if v4_status(day) is None:
        return 0
    check_pack_binding(day.book, day.day.isoformat(), day.pack_sha256, released_sha256)
    rows = v4_rows(day, questions, released_sha256)
    written = zip(questions, rows, strict=True)
    return sum(records.write(folder, day.forecaster, question, [row]) for question, row in written)
