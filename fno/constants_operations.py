"""Shared names of the daily operations, split out of `fno/constants.py` at its size limit (and imported there):
the desk run's steps (E3), the whole day's steps and their statuses (O1), and the health check's statuses (O8).
Change a value here, not where it is used."""

from __future__ import annotations

__all__ = [
    "ENV_FNO_REHEARSAL",
    "ENV_FNO_REHEARSAL_NOT_LIVE",
    "PUBLISH_BRANCH",
    "RUN_LOG_DECISIONS_STEP",
    "RUN_LOG_EXITS_STEP",
    "RUN_LOG_TRADE_MARKS_STEP",
    "REVIEWS_STEP",
    "SCHOOL_STEP",
    "DESK_RUN_STEPS",
    "DAILY_RUN_STEPS",
    "V4_PACK_LIVE_KEY",
    "V4_RELEASE_STEP",
    "V4_PACK_FORECASTS_STEP",
    "V4_DEADLINE_STEP",
    "OWNER_TIMING_STEP",
    "STEP_OK",
    "STEP_FAILED",
    "STEP_REFUSED",
    "STEP_NOT_LIVE",
    "STEP_NOT_BUILT",
    "STEP_EXERCISED",
    "EXERCISED_PARTS",
    "HEALTH_OK",
    "HEALTH_LATE",
    "HEALTH_MISSED",
    "HEALTH_UNKNOWN",
    "HEALTH_NOT_DUE",
    "HEALTH_NOT_EXPECTED",
    "HEALTH_PROBLEMS",
    "HEALTH_RUNS_FILE",
    "AI_FIRE_STEP",
    "AI_COLLECT_STEP",
    "ENV_ROUTINE_BOOK2_DECISION_TRIGGER_ID",
    "ENV_ROUTINE_BOOK2_DECISION_TOKEN",
    "ENV_ROUTINE_BOOK3_DECISION_TRIGGER_ID",
    "ENV_ROUTINE_BOOK3_DECISION_TOKEN",
    "ROUTINE_POINTER_MAX_BYTES",
]

# Story E3: the daily run's step that collects the books' decisions, as its run log names it (read by D3b and S2)
RUN_LOG_DECISIONS_STEP = "decisions"
RUN_LOG_EXITS_STEP = "exits"  # the daily run's exit review step (scoreboard B reads it, story S6)
RUN_LOG_TRADE_MARKS_STEP = "trade_marks"  # E2d: every open trade marked right after the exits
REVIEWS_STEP = "reviews"  # after the exits: E6's scorecards and automatic pauses (LR3's drift monitor joins it later)
SCHOOL_STEP = "school"  # MS-P1j2: the market school's slot; its sections read this step back from the run log (j4)
# E3's steps (with E2d's marking), then story O1's whole day in order (the health check O8 reads it); Book 1 decides
# right after the pack
DESK_RUN_STEPS = (
    "versions",
    "pack",
    RUN_LOG_DECISIONS_STEP,
    "snapshot",
    "fills",
    RUN_LOG_EXITS_STEP,
    RUN_LOG_TRADE_MARKS_STEP,
)
# Story G10 completion: one `daily.live_from` key for protocol v4's 14:30 capture part, its release and its 15:10 check
V4_PACK_LIVE_KEY, V4_RELEASE_STEP, V4_DEADLINE_STEP = "v4_pack", "v4_release", "v4_deadline"
V4_PACK_FORECASTS_STEP = "forecasts_v4_pack"  # story G7b completion: its own `daily.live_from` key (null until the go)
OWNER_TIMING_STEP = "owner_timing_fills"  # story E8: right after the quote parts start, before every other step
AI_FIRE_STEP, AI_COLLECT_STEP = "ai_fire", "ai_collect"  # story F1t: the AI books' decisions, around Book 1's
DAILY_RUN_STEPS = (
    "quotes",
    OWNER_TIMING_STEP,
    "margin_check",
    "weather",
    "forecasts_v4",
    V4_RELEASE_STEP,  # G10 completion: after the `v4` part's capture ends (by 14:45), before E3's pack (14:58)
    V4_PACK_FORECASTS_STEP,  # G7b completion: the pack-derived v4 rows, after the release, committed before 15:10
    *DESK_RUN_STEPS[:2],
    AI_FIRE_STEP,  # right after the pack: a slow Book 1 must not delay the fire (judge 301)
    "book1",
    AI_COLLECT_STEP,  # before E3's deadline step
    *DESK_RUN_STEPS[2:],
    REVIEWS_STEP,
    "quotes_done",
    "card",
    "price_distribution",  # story G13: reads the committed 3 pm chains, nothing reads it, so after the card
    "premium_ranges",  # story G13d: from G13's record, at once (sealed by 15:30; the command refuses after it)
    SCHOOL_STEP,  # MS-P1j: the five roads' 15:00 slot; after G13d (seconds), as both refuse after 15:30 (law 6)
    "recommend",  # REC1b: the day's one recommendation, after the school so its sealed decisions are candidates
    "price_distribution_scores",  # G13's scores: outcomes lag one session (NSE's close file lands in the evening)
    "price_ranges",  # story G13b: the 15:45 ranges from the same chains, after G13
    "price_range_scores",  # G13b's scores and seals; the same one-session lag
    "premium_range_scores",  # G13d's scores and seals: issues whose next session has passed
    V4_DEADLINE_STEP,  # G10 completion: the 15:10 verdicts and the 14:30 overlap watch (from 15:12)
    "candles",  # A16b-d: after A16's last mark (fno/intraday/backfill_daily.py)
    "close_read",  # story A4h: today's closes from NSE's index list, 15:40, after the candles
    "close_recheck",  # A4h's second read, 16:00, last (judge 440 add. 1)
)  # fmt: skip; the quote parts start first (judge 178)
# Story REH1: set only by a rehearsal, inherited by its children; and the line a not-yet-live report's posts carry
ENV_FNO_REHEARSAL = "FNO_REHEARSAL"
ENV_FNO_REHEARSAL_NOT_LIVE = "FNO_REHEARSAL_NOT_LIVE"
# Every scheduled run publishes to main, whatever branch its checkout is on (a scheduled session runs on its own
# unpublished session branch: 22 Oct 2026, "couldn't find remote ref claude/...")
PUBLISH_BRANCH = "main"
STEP_OK, STEP_FAILED, STEP_REFUSED, STEP_NOT_LIVE = "ok", "failed", "refused", "not_live"  # an O1 step's status
# Story REH1j: a rehearsed step not live in real runs keeps what it did under this key; a command not built yet
STEP_EXERCISED, STEP_NOT_BUILT = "exercised", "not_built"
EXERCISED_PARTS = "exercised_parts"  # `quotes_done`'s parts not live on the replayed day (REH1j)

# The daily health check (story O8, fno/health/): its statuses and its own run record
HEALTH_OK, HEALTH_LATE, HEALTH_MISSED, HEALTH_UNKNOWN = "ok", "late", "missed", "unknown"
HEALTH_NOT_DUE, HEALTH_NOT_EXPECTED = "not due", "not expected"
HEALTH_PROBLEMS = (HEALTH_LATE, HEALTH_MISSED, HEALTH_UNKNOWN)
HEALTH_RUNS_FILE = "research/ops/health_runs.csv"

# Story F1t: each AI book's decision routine (two more routines, made by the owner; the forecast routines are
# separate), fired by the daily run, so these are settings of the daily routine's environment (names only here)
ENV_ROUTINE_BOOK2_DECISION_TRIGGER_ID = "FNO_ROUTINE_BOOK2_DECISION_TRIGGER_ID"
ENV_ROUTINE_BOOK2_DECISION_TOKEN = "FNO_ROUTINE_BOOK2_DECISION_TOKEN"
ENV_ROUTINE_BOOK3_DECISION_TRIGGER_ID = "FNO_ROUTINE_BOOK3_DECISION_TRIGGER_ID"
ENV_ROUTINE_BOOK3_DECISION_TOKEN = "FNO_ROUTINE_BOOK3_DECISION_TOKEN"
# A routine's fired text: one line of JSON, at most this long (the routine API's limit, to be confirmed before go-live);
# a longer input is `not_fired`, never truncated (F1t's decision pointer, G11's v4 forecast pointer, response 272).
ROUTINE_POINTER_MAX_BYTES = 64 * 1024
