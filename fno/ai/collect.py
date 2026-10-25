"""The collection (stories F1 and G5), run by the forecast-capture GitHub Actions job after 15:15 IST: for each AI book,
read its submission from `main` with GitHub's receipt times, rebuild the input it had to answer from, judge it, then
write five v2 records (`research/forecasts/ai_v1/<YYYY>/<d>_<book>_forecasts.csv`) and the audit file beside them.
Written once; a day without a v2 pack records nothing (like Book 1)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..constants import AI_BOOKS, BOOK2_HYBRID
from .book_run import answer_labels, envelope_of
from .export import ExportRefused, build_export
from .history import RepoHistory
from .outcome import INVALID, NO_SUBMISSION, NOT_FIRED, Outcome, judge, mark_exposures
from .paths import fired_path, pack_path
from .pointer import BookPointer
from .receipts import PushReceipts
from .record_writer import AiRecordWriter
from .rules import RulesMissing, rules_of_day
from .submissions import read_submission
from .versions import VersionRefused, current_version, version_by_label

LINE = "Omenix F&O AI forecasts (GitHub Actions): {day}: {result}"


STOPPED = "v2 AI collection stopped: the books answer protocol v4 from {live_from} (nothing recorded, never a miss)"


@dataclass
class AiForecastCollector:
    root: Path
    history: RepoHistory
    receipts: PushReceipts
    writer: AiRecordWriter
    clock: Callable[[], datetime]
    v4_live_from: date | None = None  # the AI books' v4 go-live: the v2 AI run, fire and collection, stops that day

    def collect(self, day: date) -> list[str]:
        if self.v4_live_from is not None and day >= self.v4_live_from:
            return [LINE.format(day=day, result=STOPPED.format(live_from=self.v4_live_from))]
        pack_file = self.root / pack_path(day)
        if not pack_file.is_file():
            return [LINE.format(day=day, result="no v2 pack for the day; nothing recorded")]
        pack_bytes = pack_file.read_bytes()
        pack, pack_sha = json.loads(pack_bytes), hashlib.sha256(pack_bytes).hexdigest()
        fired = self._fired(day)
        outcomes = {book: self._outcome(day, book, pack_sha, fired.get(book, {})) for book in AI_BOOKS}
        mark_exposures(outcomes)
        lines = []
        for book, outcome in outcomes.items():
            written = self.writer.write(day, pack_sha, pack, outcome, fired.get(book, {}), self.clock())
            counted = sum(p is not None for p in outcome.probabilities.values())
            lines.append(
                LINE.format(day=day, result=f"{book} {outcome.status}: {counted} of 5 probabilities; {written}")
            )
            lines.append(self.writer.receipt_line(day, outcome))
        return lines

    def _outcome(self, day: date, book: str, pack_sha: str, fired: dict) -> Outcome:
        submission = read_submission(self.history, self.receipts, day, book)
        sealed = submission.sealed()
        try:
            version = version_by_label(sealed.version) if sealed else current_version(book)
            rules = rules_of_day(self.root, day) if book == BOOK2_HYBRID else None
            pointer = BookPointer(book, day, pack_sha, version.label, rules)
            labels = answer_labels(pointer, build_export(self.root, pointer, version))
        except (VersionRefused, ExportRefused, RulesMissing) as refused:
            outcome = Outcome(book, INVALID, current_version(book).label)
            outcome.withdraw(INVALID, f"the input could not be rebuilt: {refused}")
            return outcome
        outcome = judge(book, day, submission, labels, envelope_of(pointer), version)
        if outcome.status == NO_SUBMISSION and fired and not fired.get("fired"):
            outcome.withdraw(NOT_FIRED, f"the routine was not fired: {fired.get('reason', '')}")
        return outcome

    def _fired(self, day: date) -> dict:
        path = self.root / fired_path(day)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
