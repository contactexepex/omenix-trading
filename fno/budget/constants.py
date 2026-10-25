"""The budget's fixed names (stories F8 and BG1), used only by `fno/budget/`: module-specific constants (CLAUDE.md),
moved out of `fno/constants.py` to keep that file under the 350-line limit."""

# Stories F8 (minimal) and BG1 (fno/budget/): what an AI session's minutes were for, design v2 section 8.1's cost
# items, and the order AI roles stop in at 100% of the AI cap (section 7.6); code jobs keep running
PURPOSE_BOOKS_AND_ROLES, PURPOSE_DEVELOPMENT = "books_and_roles", "development"  # only the first counts against the cap
PURPOSE_DATA_ROUTINES = (
    "data_routines"  # code jobs run by a Claude routine (3 pm and 15-minute recorders): keep running
)
USAGE_PURPOSES = (PURPOSE_BOOKS_AND_ROLES, PURPOSE_DEVELOPMENT, PURPOSE_DATA_ROUTINES)
ITEM_CLAUDE_PLAN = "Claude subscription"
ITEM_GITHUB_DRIVE = "GitHub Actions and Drive"
ITEM_AZURE_POSTGRES = "Azure Database for PostgreSQL"
ITEM_GROWW_API = "Groww API"
ITEM_RECORDER_HOSTING = "Recorder and monitor hosting"
ITEM_PAID_DATA = "Paid data"
BUDGET_ITEMS = (ITEM_CLAUDE_PLAN, ITEM_GITHUB_DRIVE, ITEM_AZURE_POSTGRES, ITEM_GROWW_API, ITEM_RECORDER_HOSTING,
                ITEM_PAID_DATA)  # fmt: skip
EXISTING_COST_ITEMS = (ITEM_CLAUDE_PLAN, ITEM_AZURE_POSTGRES)  # running before 15 Oct 2026; others need a written yes
BUDGET_OK, BUDGET_ALERT, BUDGET_STOP, BUDGET_UNKNOWN = "ok", "alert", "stop", "unknown"
# Story BG1-u (owner, 24 Oct 2026: "No monthly budget cap for AI. Keep it unlimited."): `budget.cap` is `none` (no
# level, nothing alerts or stops) or `share` (the 15 Oct cap, kept for a later decision)
CAP_NONE, CAP_SHARE = "none", "share"
CAP_MODES = (CAP_NONE, CAP_SHARE)
BUDGET_NO_CAP = "no_cap"
AI_ROLE_STOP_ORDER = ("analysts", "idea generator", "post-mortem writer", "devil's advocate objections",
                      "AI forecasters")  # fmt: skip
# Story BG1-w (owner 24 Oct 2026, "Waiting minutes - Option A": a book run counts its working minutes, brief to seal):
# what a run that never sealed counts, the builder's rule for the owner (BG-budget.md, BG1-w). The upper bound counts
# it start to end, so the month's level stays known; the unknown rule refuses it (its session stays not captured)
NO_SEAL_UPPER_BOUND, NO_SEAL_UNKNOWN = "no_seal_upper_bound", "no_seal_unknown"
NO_SEAL_RULES = (NO_SEAL_UPPER_BOUND, NO_SEAL_UNKNOWN)
NO_SEAL_RULE = NO_SEAL_UPPER_BOUND  # the one switch, until the owner answers (orchestrator, 24 Oct)
