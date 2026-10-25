"""Firing the AI books (stories F1 and G5), run by the forecast-capture GitHub Actions job right after it committed
the day's v2 pack: one pointer per book to its own routine (O6's `/fire` trigger), Hybrid's with the rules' numbers,
the AI team's without. The fire log (`<d>_fired.json`, committed with the records after 15:15) keeps each routine's
session link for the audit. Fired once per day; every failure posts one #fno-desk line and is recorded, never retried
with more time. A book stopped by two transcript breaches (`stop_rule.py`) is not fired, nor is any book on a run
that starts after 15:13 IST (its answer could only be late). From the v4 go-live date the v2 AI fire stops (owner's
choice A, G11: the books fire for v4 only, `v4_fire.py`)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..alerts.sender import AlertSender
from ..constants import AI_BOOKS, BOOK2_HYBRID
from ..pipeline.trigger import FireFailed, RoutineTrigger
from .paths import fired_path, pack_path
from .pointer import BookPointer
from .rules import RulesMissing, rules_of_day
from .stop_rule import stop_reason
from .timing import LATEST_START, latest_start
from .versions import current_version

LINE = "Omenix F&O AI forecasts (GitHub Actions): {day}: {result}"
LATE_START = "late start: the run began after {latest:%H:%M} IST, so no AI book was fired (no forecast today)"
V4_LIVE = "v2 AI fire stopped: the books fire for protocol v4 from {live_from} (owner's choice A)"


@dataclass
class AiBookFirer:
    root: Path
    triggers: dict[str, RoutineTrigger]  # book -> its routine's trigger
    alerts: AlertSender
    clock: Callable[[], datetime]
    v4_live_from: date | None = None

    def fire(self, day: date) -> list[str]:
        if self.v4_live_from is not None and day >= self.v4_live_from:
            return [LINE.format(day=day, result=V4_LIVE.format(live_from=self.v4_live_from))]
        pack_file, log_file = self.root / pack_path(day), self.root / fired_path(day)
        if not pack_file.is_file():
            return [LINE.format(day=day, result="no v2 pack for the day; nothing fired")]
        if log_file.is_file():
            return [LINE.format(day=day, result="already fired (fired once per day)")]
        pack_sha = hashlib.sha256(pack_file.read_bytes()).hexdigest()
        late = self.clock() > latest_start(day)
        log = {book: self._late_start(day, book) if late else self._fire_one(day, book, pack_sha) for book in AI_BOOKS}
        if late:
            self.alerts.send(LINE.format(day=day, result=LATE_START.format(latest=LATEST_START)))
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(json.dumps(log, sort_keys=True, indent=1) + "\n", encoding="utf-8")
        fired = [book for book, entry in log.items() if entry["fired"]]
        return [LINE.format(day=day, result=f"fired {', '.join(fired) or 'none'} of {', '.join(AI_BOOKS)}")]

    def _late_start(self, day: date, book: str) -> dict:
        """Not fired: its answer could only be late (the collection records `not_fired`, reason late start)."""
        entry = {"version": current_version(book).label, "fired_at": self.clock().isoformat()}
        return entry | {"fired": False, "late_start": True, "reason": LATE_START.format(latest=LATEST_START)}

    def _fire_one(self, day: date, book: str, pack_sha: str) -> dict:
        version = current_version(book).label
        entry = {"version": version, "fired_at": self.clock().isoformat()}
        stopped = stop_reason(self.root, book, version, day)
        if stopped:
            self.alerts.send(LINE.format(day=day, result=f"{book} not fired: {stopped}"))
            return entry | {"fired": False, "reason": stopped}
        try:
            rules = rules_of_day(self.root, day) if book == BOOK2_HYBRID else None
            session = self.triggers[book].fire(BookPointer(book, day, pack_sha, version, rules))
        except (FireFailed, RulesMissing) as failed:
            self.alerts.send(LINE.format(day=day, result=f"{book} not fired: {failed}; its day records no forecast"))
            return entry | {"fired": False, "reason": str(failed)}
        return entry | {"fired": True, "session": session}
