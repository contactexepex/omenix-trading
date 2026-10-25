"""Story G11, firing the AI books under protocol v4 (response 272), run by `v4-fire.yml` when the day's release record
lands (G10 part 2): each book's routine is fired once, with a pointer holding its whole input (the session has no
Drive credentials). Research only.

- Refused outright (nothing logged): a day that is not today's IST date (a replayed or late push), and any day before
  the AI books' v4 go-live date (`daily.live_from.ai_books_v4`, the same date that stops the v2 AI fire: owner's
  choice A).
- No released pack (none recorded, `system_late`, or bytes failing their receipt): nothing is fired, one #fno-desk line,
  and no log, so a later receipt push before 14:55 may still fire the day.
- Per book: a start after `V4_LATEST_FIRE` (14:55), the stop rule, BG1's budget stop (`budget_stop.py`: forecasters
  last), a pointer over the cap or a refused trigger is a logged `not_fired`, with one #fno-desk line, never retried.
  The stop rule's day carries `"stop_rule": true`, the flag `v4_rows` reads (never the reason's wording); BG1's
  carries `"budget_stop": true`. A budget reading that fails fires the books with one line (fail open).
- The log (`ai_v4/<YYYY>/<d>_fired.json`) keeps what the collection needs: the version, the questions, the pack's
  and the input's SHA-256, the labels every answer must carry, Hybrid's envelope (numbers from the rule rows, never a
  quote) and the routine's session link. Collect judges from it and never rebuilds the input, because the files an
  input is built from (closes, A16's rows) can still change after the fire (review of dfb26381)."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..alerts.sender import AlertSender
from ..constants import AI_BOOKS
from ..forecast_v4.terms import V4_LATEST_FIRE
from ..models import IST
from ..pipeline.trigger import FireFailed, RoutineTrigger
from ..v4_pack.model import Pack
from ..v4_pack.release import NotReleased, ReleasedPacks
from .budget_stop import BudgetStop
from .run_terms import FORECAST_PROTOCOL_V4, V4_TERMS
from .stop_rule import stop_reason
from .v4_book_inputs import V4BookInputs
from .v4_go_live import missed_before_go_live
from .v4_pointer import V4Pointer, parse_v4_pointer, v4_labels
from .versions import current_version

LINE = "Omenix F&O AI forecasts v4 (GitHub Actions): {day}: {result}"
NOT_TODAY = "not fired: {day} is not today ({today}), so a replayed or late push fires nothing"
NOT_LIVE = "not fired: v4 is not live before {live_from} (config.yaml daily.live_from.ai_books_v4)"
NO_LIVE_DATE = "not fired: no v4 go-live date is set (config.yaml daily.live_from.ai_books_v4)"
LATE_START = "late start: the run began after {latest:%H:%M} IST, so its answer could only be late"


@dataclass
class V4BookFirer:
    root: Path
    triggers: dict[str, RoutineTrigger]  # book -> its routine's trigger
    released: Callable[[], ReleasedPacks]  # built on first use: a refused day never needs Drive
    inputs: V4BookInputs
    alerts: AlertSender
    clock: Callable[[], datetime]
    live_from: date | None
    sessions_before: Callable[[date], list[date]]  # v4's scored sessions before a day: the stop rule's window
    budget: BudgetStop  # BG1's month: the AI forecasters stop last
    sessions_between: Callable[[date, date], list[date]]  # v4's scored sessions, both ends included

    def fire(self, day: date) -> list[str]:
        missed = missed_before_go_live(self.inputs.registry, self.live_from, day, self.sessions_between)
        return ([LINE.format(day=day, result=missed)] if missed else []) + self._fire(day)

    def _fire(self, day: date) -> list[str]:
        refused = self._refused(day)
        if refused:
            return [LINE.format(day=day, result=refused)]
        log_file = self.root / V4_TERMS.fired_path(day)
        if log_file.is_file():
            return [LINE.format(day=day, result="already fired (fired once per day)")]
        try:
            packs = self.released()
            release = packs.release(day)
            pack = packs.pack(release)
        except NotReleased as missing:  # no log: a later receipt push before 14:55 may still fire the day
            line = LINE.format(day=day, result=f"nothing fired: {missing}")
            self.alerts.send(line)
            return [line]
        late = self.clock().replace(microsecond=0) > datetime.combine(day, V4_LATEST_FIRE, IST)
        budget = self.budget.check(day)
        if budget.note:
            self.alerts.send(LINE.format(day=day, result=budget.note))
        log = {book: self._book(day, book, pack, release.pack_sha256, late, budget.stop) for book in AI_BOOKS}
        self._write(log_file, {"released": True, "pack_sha256": release.pack_sha256, "books": log})
        fired = [book for book, entry in log.items() if entry["fired"]]
        return [LINE.format(day=day, result=f"fired {', '.join(fired) or 'none'} of {', '.join(AI_BOOKS)}")]

    def _refused(self, day: date) -> str:
        today = self.clock().astimezone(IST).date()
        if day != today:
            return NOT_TODAY.format(day=day, today=today)
        if self.live_from is None:
            return NO_LIVE_DATE
        return NOT_LIVE.format(live_from=self.live_from) if day < self.live_from else ""

    def _book(self, day: date, book: str, pack: Pack, pack_sha256: str, late: bool, budget_stop: str) -> dict:
        version = current_version(book, FORECAST_PROTOCOL_V4)
        entry = {"version": version.label, "fired_at": self.clock().isoformat(), "pack_sha256": pack_sha256,
                 "fired": False, "stop_rule": False}  # fmt: skip
        entry["questions"] = self.inputs.questions(version, day)
        if refused := self.inputs.refusal(version, entry["questions"]):
            return self._not_fired(day, book, entry, refused)
        if not entry["questions"]:
            return entry | {"reason": "no v4 question is registered for its slot yet"}
        if late:
            return self._not_fired(day, book, entry | {"late_start": True}, LATE_START.format(latest=V4_LATEST_FIRE))
        stopped = stop_reason(self.root, book, version.label, day, V4_TERMS, self.sessions_before(day))
        if stopped:
            return self._not_fired(day, book, entry | {"stop_rule": True}, stopped)
        if budget_stop:
            return self._not_fired(day, book, entry | {"budget_stop": True}, budget_stop)
        pointer = V4Pointer(self.inputs.build(version, day, entry["questions"], pack, pack_sha256))
        entry |= {"input_sha256": pointer.input_sha256, "labels": v4_labels(pointer.input),
                  "envelope": (pointer.input.get("rules") or {}).get("envelope")}  # fmt: skip
        try:
            parse_v4_pointer(pointer.to_text())  # brief's check: a refusal is a logged not_fired, never a silent day
            session = self.triggers[book].fire(pointer)  # to_text refuses a pointer over the cap: never truncated
        except (FireFailed, ValueError) as failed:
            return self._not_fired(day, book, entry, str(failed))
        return entry | {"fired": True, "session": session}

    def _not_fired(self, day: date, book: str, entry: dict, reason: str) -> dict:
        self.alerts.send(LINE.format(day=day, result=f"{book} not fired: {reason}; its day records no forecast"))
        return entry | {"reason": reason}

    @staticmethod
    def _write(log_file: Path, log: dict) -> None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(json.dumps(log, sort_keys=True, indent=1) + "\n", encoding="utf-8")
