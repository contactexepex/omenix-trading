"""Story O1-status-only: the closed set of reason codes. Each code is a producer's own message template, named by its
constant and imported, never retyped, so a code names the message without any of its values. The public run log
shows the code; the full text goes only to the #fno-desk alert and the private full log."""

from __future__ import annotations

from ..ai_trading import steps as ai_steps
from ..constants import SCHOOL_STEP
from ..desk import book_versions, daily_run, daily_steps, exits, recorded_c4, trade_marking
from ..desk.owner_timing import entry_fills, exit_fills, outcomes, pending_entries
from ..desk.owner_timing import step as owner_timing
from ..recommend import cli as recommend_cli
from ..recommend import post as recommend_post
from ..recommend import run as recommend_run
from ..rehearsal import built_commands, live_wiring, recorded_quotes
from ..school import cli as school_cli
from ..school.constants import SCHOOL_OFF_LINE
from ..school.fleet import runner as school_fleet
from ..v4_pack import deadline, release_run
from . import earlier_run, quote_parts, reviews, steps

# O1's own messages: any step may carry them (a raise, a stop at the limit, a step not yet live)
COMMON = (
    ("o1:NOT_LIVE", steps.NOT_LIVE),
    ("o1:NO_DATE", steps.NO_DATE),
    ("o1:STOPPED_AT_LIMIT", steps.STOPPED_AT_LIMIT),
    ("rehearsal:NOT_RECORDED", recorded_quotes.NOT_RECORDED),  # story REH1b: a capture the day never recorded
    ("rehearsal:NOT_LIVE_UNSET", live_wiring.NOT_LIVE_UNSET),  # story REH1j: a step exercised, not live in real runs
    ("rehearsal:NOT_LIVE_UNTIL", live_wiring.NOT_LIVE_UNTIL),
    ("rehearsal:NOT_BUILT", built_commands.NOT_BUILT),  # REH1j: its command not in fno yet
)
BLOCKS = (
    ("desk:NO_LOG", daily_run.NO_LOG),
    ("desk:BEFORE_EXITS", daily_run.BEFORE_EXITS),
    ("desk:NOT_REVIEWED", daily_run.NOT_REVIEWED),
    ("desk:UNSCORED", daily_run.UNSCORED),
    ("desk:UNFILLED", daily_run.UNFILLED),
)
FILL_REASONS = (
    ("fills:NO_SNAPSHOT", daily_steps.NO_SNAPSHOT),
    ("fills:NOT_WRITTEN", daily_steps.NOT_WRITTEN),
    ("fills:NOT_ORDERED", daily_steps.NOT_ORDERED),
    ("fills:LATE_AT_SNAPSHOT", daily_steps.LATE_AT_SNAPSHOT),
    ("fills:DOUBLE", daily_steps.DOUBLE),
    ("fills:BLOCKED", daily_steps.BLOCKED),
    ("fills:ENTRY_REFUSED", daily_steps.ENTRY_REFUSED),
    ("fills:NOT_VALIDATED", daily_steps.NOT_VALIDATED),
    ("c4:NO_RUN", recorded_c4.NO_RUN),
    ("c4:NO_RECORD", recorded_c4.NO_RECORD),
    ("c4:EDITED", recorded_c4.EDITED),
    ("c4:NOT_RUN", recorded_c4.NOT_RUN),
    ("c4:FAILED", recorded_c4.FAILED),
    ("owner_timing:HANDED_OVER", pending_entries.HANDED_OVER),
    ("desk:FILLS_LATE", daily_run.FILLS_LATE),  # owner, 24 Oct: no fills by a rerun after fills_by
    ("desk:NEEDS_FAILED", daily_run.NEEDS_FAILED),
    ("desk:NEEDS_MISSING", daily_run.NEEDS_MISSING),
    ("desk:NEEDS_REFUSED", daily_run.NEEDS_REFUSED),
)
OWNER_TIMING = (
    ("owner_timing:APPLIED", owner_timing.APPLIED),
    ("owner_timing:SEALED_ONLY", owner_timing.SEALED_ONLY),
    ("owner_timing:SEAL_FAILED", owner_timing.SEAL_FAILED),
    ("owner_timing:BLOCKED", entry_fills.BLOCKED),
    ("owner_timing:OPENED", entry_fills.OPENED),
    ("owner_timing:REPRICED", entry_fills.REPRICED),
    ("owner_timing:FILLED", exit_fills.FILLED),
    ("owner_timing:WAITING", exit_fills.WAITING),
    *((f"owner_timing:{name}", getattr(outcomes, name)) for name in (
        "MISSED_NO_CARD", "MISSED_OWNER_AWAY", "MISSED_NO_QUOTE", "MISSED_NO_FUTURE", "MISSED_PRICE_MOVED",
        "MISSED_EXPIRED", "MISSED_FUNDS", "MISSED_RISK_CAP", "DECIDED_AFTER_CARD")),
)  # fmt: skip
QUOTE_PARTS = (
    ("parts:STILL_RUNNING", quote_parts.STILL_RUNNING),
    ("parts:NEVER_STARTED", quote_parts.NEVER_STARTED),
    ("parts:STILL_HELD", quote_parts.STILL_HELD),
    ("parts:NOT_IN_THIS_RUN", quote_parts.NOT_IN_THIS_RUN),
    ("parts:HUNG", quote_parts.HUNG),  # G10's `v4` part still running at 14:45
    ("parts:RECORDED_EARLIER", earlier_run.RECORDED_EARLIER),
    ("parts:NO_RECORD", earlier_run.NO_RECORD),
    ("parts:ENDED_NONE", earlier_run.ENDED_NONE),
)
AI_STEPS = (  # story F1t: the AI books' two steps (criterion 17)
    ("ai:DONE", ai_steps.DONE),
    ("ai:NOT_LIVE_BOOKS", ai_steps.NO_LIVE_BOOK),
    ("ai:NOT_FIRED", ai_steps.NOT_FIRED),
    ("ai:NOT_PROMOTED", ai_steps.NOT_PROMOTED),
    ("ai:OBSERVER_LOST", ai_steps.OBSERVER_LOST),
    ("ai:BUDGET_UNREAD", ai_steps.BUDGET_UNREAD),
    ("ai:REHEARSAL_NO_FIRE", ai_steps.REHEARSAL_NO_FIRE),
    ("ai:CONFIG", ai_steps.CONFIG_WRONG),
)
STEP_TEMPLATES = {
    "ai_fire": AI_STEPS,
    "ai_collect": AI_STEPS,
    "versions": (
        ("versions:NONE_YET", book_versions.NONE_YET),
        ("versions:UNCHANGED", book_versions.UNCHANGED),
        ("versions:REGISTERED", book_versions.REGISTERED),
        ("versions:REFUSED", book_versions.REFUSED),
    ),
    "decisions": (
        ("decisions:NOT_COMMITTED", daily_steps.NOT_COMMITTED),
        ("decisions:COLLECTED_LATE", daily_steps.COLLECTED_LATE),
    ),
    "fills": FILL_REASONS + BLOCKS,
    "exits": (("exits:NO_RULES", exits.NO_RULES),),
    "trade_marks": (
        ("marks:NOT_VALUED", trade_marking.NOT_VALUED),
        ("marks:FAILED", trade_marking.FAILED),
    ),
    "reviews": (("reviews:NOTHING_TO_MARK", reviews.NOTHING_TO_MARK),),
    "owner_timing_fills": OWNER_TIMING,
    "quotes_done": QUOTE_PARTS,
    "v4_release": (  # G10 completion: the release's own lines (an A or system_late line keeps the command's code)
        ("v4_release:ALREADY", release_run.ALREADY),
        ("v4_release:WAITING", release_run.WAITING),
        ("v4_release:REFUSED", release_run.REFUSED),
        ("v4_release:NOT_LIVE", release_run.NOT_LIVE),
    ),
    "recommend": (  # REC1b: posted (or re-sent), an input problem, not posted, a changed rung rule, no session
        ("recommend:POSTED", recommend_post.HEAD),
        ("recommend:INPUT_PROBLEM", recommend_run.INPUT_PROBLEM),
        ("recommend:NOT_POSTED", recommend_run.NOT_SAVED),
        ("recommend:RULE_CHANGED", recommend_run.RULE_CHANGED),
        ("recommend:NOT_A_SESSION", recommend_cli.NOT_A_SESSION),
    ),
    SCHOOL_STEP: (  # MS-P1j: its switch off, a closed day, or a loud stop (any stop's status: "stopped: <reason>")
        ("school:OFF", SCHOOL_OFF_LINE),
        ("school:NOT_A_SESSION", school_cli.NOT_A_SESSION),
        ("school:STOPPED", school_fleet.DASHCAM_STOP),
        ("school:TOO_LATE", steps.STARTS_TOO_LATE),
    ),
    "v4_deadline": (
        ("v4_deadline:CHECKED", deadline.CHECKED),
        ("v4_deadline:TOO_EARLY", deadline.TOO_EARLY),
        ("v4_deadline:UNKNOWN", deadline.UNKNOWN),
        ("v4_deadline:REFUSED", deadline.REFUSED),
        ("v4_deadline:NOT_LIVE", deadline.NOT_LIVE),
    ),
}
