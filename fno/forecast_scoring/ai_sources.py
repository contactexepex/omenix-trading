"""The AI books' forecasts for story G4 (stories F1 and G5): `research/forecasts/ai_v1/<YYYY>/<d>_<book>_forecasts.csv`
in the v2 record schema.

Whether a book-day may be scored is F1's one rule, `fno.ai.scoring_gate.scoring_status` (owner's conditions 1 and 2):
the collection said `on_time` and the transcript audit (`_transcript_audit.json`) found no breach. Its answer is used
as is:
- `scored`: then the records must also name the day's v2 pack, and that pack must have matched its capture receipt
  (Book 1's live check); otherwise the day is unscored;
- `unscored` (late, exposed, model mismatch, a transcript breach, ...): listed with its reason, never scored;
- `pending` (not collected, transcript audit due, the week's audit draw not made yet): listed apart, not scored yet;
  it is scored on a later run once the audit clears it.
Neither unscored nor pending days count in coverage. The isolation label (today `sealed_same_day`) comes from the gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ..ai.paths import AI_FOLDER
from ..ai.scoring_gate import PENDING, scoring_status
from ..forecast.record_files import read_records_v2
from .score_inputs import ScoredForecast, from_live

RECORDS_SUFFIX = "_forecasts.csv"


@dataclass
class AiForecasts:
    forecasts: list[ScoredForecast] = field(default_factory=list)
    unscored: list[dict] = field(default_factory=list)  # {day, book, reason}: never scored
    pending: list[dict] = field(default_factory=list)  # {day, book, reason}: not scored yet (audit to come)
    isolation: dict[str, set[str]] = field(default_factory=dict)  # book -> isolation labels


def ai_forecasts(root: Path, verified_packs: dict[date, str], seeds: dict) -> AiForecasts:
    """`verified_packs`: day -> SHA-256 of the day's receipt-verified v2 pack. `seeds`: the weekly audit draws' seeds,
    each confirmed in the Drive archive (`fno.ai.wiring.build_audit_seeds`). F1's gate decides each book-day."""
    out = AiForecasts()
    for records_path in sorted((Path(root) / AI_FOLDER).glob(f"*/*{RECORDS_SUFFIX}")):
        stem = records_path.name.removesuffix(RECORDS_SUFFIX)
        day, book = date.fromisoformat(stem[:10]), stem[11:]
        gate = scoring_status(root, day, book, seeds)
        if gate.isolation:
            out.isolation.setdefault(book, set()).add(gate.isolation)
        entry = {"day": day.isoformat(), "book": book, "reason": gate.reason}
        if not gate.scored:
            (out.pending if gate.status == PENDING else out.unscored).append(entry)
            continue
        records = read_records_v2(records_path.read_text(encoding="utf-8"))
        problem = _pack_problem(records, verified_packs.get(day))
        if problem:
            out.unscored.append({**entry, "reason": problem})
            continue
        out.forecasts += [f for f in (from_live(r) for r in records) if f is not None]
    return out


def _pack_problem(records: list, pack_sha: str | None) -> str | None:
    if pack_sha is None:
        return "the day's v2 pack is missing or does not match its capture receipt"
    if any(r.record.pack_sha256 != pack_sha for r in records):
        return "records name another pack than the day's v2 pack"
    return None
