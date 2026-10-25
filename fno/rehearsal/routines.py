"""The four scheduled routines a rehearsal replays (story REH1c), each as CLAUDE.md runs it: its start time, its
commands in order (a background one is started first and waited for at the end), and the receipts the routine's
session commits by hand after them. CLAUDE.md is the source; a test holds each command to its routine's section."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta

from ..forecast_lab.constants import EVENING, MORNING

# REH1r: the first day each command ran in its routine, the later of the CLAUDE.md commit that added it to its
# routine's section and the routine's own first run (its first output on `main`); the table in
# docs/stories/REH1-rehearsal-mode.md, REH1r, Design 2. The owner created the pre-open, morning and evening tasks later
# on 22 Oct (conversations/2026-10-22.md, "Orchestrator, later on 22 Oct").
PREOPEN_SINCE = date(2026, 10, 23)  # a2b2ad8c6 and e6010ac0a (22 Oct); first outputs 23 Oct 08:40 and 08:51 IST
INDEX_CLOSE_SINCE = date(2026, 10, 23)  # 96af942cd (22 Oct 04:29 IST); the morning's first output 3decf6a60, 23 Oct
CERTIFY_SINCE = date(2026, 10, 24)  # 51cab79b0 (23 Oct 22:42 IST, on main about 23:58); first record 24 Oct 08:41 IST
EVENING_SINCE = date(2026, 10, 22)  # cae76af89, 49aa26951 (22 Oct); the routine's own outputs 22 Oct 19:54-19:55 IST


@dataclass(frozen=True)
class Command:
    args: tuple[str, ...]  # "{day}" and "{week_ago}" are the replayed day and the day a week before it
    background: bool = False
    live_key: str | None = None  # REH1k: its `forecast_lab.live_from` edition; before it, exercised, not failed
    since: date | None = None  # REH1r: the first day it ran in its routine; before it, exercised, not failed

    def exercised_on(self, day: date, not_live: frozenset[str]) -> bool:
        """Run as on the day but kept out of "failed": its edition not live (REH1k), or not yet in its routine."""
        return self.live_key in not_live or (self.since is not None and day < self.since)

    def for_day(self, day: date) -> list[str]:
        week_ago = day - timedelta(days=7)
        return [a.format(day=day.isoformat(), week_ago=week_ago.isoformat()) for a in self.args]


@dataclass(frozen=True)
class Routine:
    name: str
    section: str  # its CLAUDE.md section
    start: time
    commands: tuple[Command, ...]
    receipts: tuple[str, ...] = ()  # the routine's own `git add` paths, committed after its commands


ROUTINES = {
    r.name: r
    for r in (
        Routine("daily", "Daily desk routine", time(14, 5), (Command(("daily", "run", "--day", "{day}")),)),
        Routine("preopen", "Pre-open capture (story A22)", time(8, 36),
                (Command(("global-cues", "preopen"), background=True, since=PREOPEN_SINCE),
                 Command(("preopen", "record"), since=PREOPEN_SINCE))),
        Routine("morning", "Morning and evening forecast routines", time(8, 38),
                (Command(("data-librarian", "index-close", "--from", "{week_ago}"), since=INDEX_CLOSE_SINCE),
                 Command(("lab", "open"), live_key=MORNING),
                 Command(("records", "certify", "closes", "--since", "7", "--level", "certified", "--commit"),
                         since=CERTIFY_SINCE)),
                ("receipts/data/forecast_lab/v1/morning/",)),
        Routine("evening", "Morning and evening forecast routines", time(19, 53),
                (Command(("closes", "read", "--commit"), since=EVENING_SINCE),
                 Command(("records", "certify", "closes", "--level", "provisional", "--commit"), since=CERTIFY_SINCE),
                 Command(("data-librarian", "fo-bhavcopy", "--from", "{day}", "--to", "{day}"), since=EVENING_SINCE),
                 Command(("data-librarian", "participant-oi", "--from", "{day}", "--to", "{day}"), since=EVENING_SINCE),
                 Command(("data-snapshot", "fii-dii-cash-by-session"), since=EVENING_SINCE),
                 Command(("lab", "close"), live_key=EVENING),
                 Command(("lab", "release-check"), since=EVENING_SINCE)),
                ("receipts/data/forecast_lab/v1/evening/", "research/data/forecast_lab/release/")),
    )
}  # fmt: skip
