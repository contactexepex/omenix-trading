"""Shared names and fixed strings. Change a value here, not where it is used."""

from __future__ import annotations

from datetime import time
from enum import StrEnum

from fno.shared.constants_channels import *  # noqa: F403 - story FL1's two channels; callers keep `fno.shared.constants`

# A daily run step's status, read by the ingestion feed gate (fno/intraday/feed_gate.py)
STEP_OK = "ok"

# Environment variable names (values are never stored in files).
# Groww Trade API (market data only; the tool never places orders)
ENV_GROWW_ACCESS_TOKEN = "GROWW_ACCESS_TOKEN"
ENV_GROWW_API_KEY = "GROWW_API_KEY"
ENV_GROWW_API_SECRET = "GROWW_API_SECRET"
ENV_GROWW_TOTP_SECRET = "GROWW_TOTP_SECRET"
# Raw-file archive on Google Drive (fno/storage): read-only service account; both only in the environment
ENV_GDRIVE_SERVICE_ACCOUNT_JSON = "FNO_GDRIVE_SERVICE_ACCOUNT_JSON"  # the key's JSON text, or it base64-encoded
ENV_GDRIVE_FOLDER_ID = "FNO_GDRIVE_FOLDER_ID"  # the shared folder's ID (from its Drive link)
# Other secrets the routines' environment holds; named here so the public-record scan (story O5) watches them too
ENV_FNO_SLACK_BOT_TOKEN = "FNO_SLACK_BOT_TOKEN"
ENV_MOTHERDUCK_TOKEN = "MOTHERDUCK_TOKEN"

# Slack channel for all F&O output (#fno-desk); its ID is public by design and allowed in committed records
FNO_DESK_CHANNEL_ID = "C0C89E8QCCD"

# How this tool names itself to public websites (NSE): honest, and accepted by them
RESEARCH_USER_AGENT = "Mozilla/5.0 (compatible; fno-desk/1.0; personal research)"

# Month codes in NSE file names and dates (e.g. fo02JAN2019bhav), independent of the computer's language settings
MONTH_CODES = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

# NSE session calendar (fno/research_data/calendar.py): kinds of rows in nse_sessions.csv, and of sessions
SESSION_HOLIDAY, SESSION_SPECIAL, SESSION_MUHURAT, SESSION_REGULAR = "holiday", "special", "muhurat", "regular"

# Index names in NSE's daily index-close file that every file must carry (the research needs both)
INDEX_NIFTY_50, INDEX_INDIA_VIX = "Nifty 50", "India VIX"

# The three paper books (design 12.1, story E1): each has its own paper account under journal/<book>/account/,
# opened with config.yaml risk.paper_account_rs (story C5)
BOOK1_RULES = "book1_rules"  # pure rules
BOOK2_HYBRID = "book2_hybrid"  # AI inside the authority envelope
BOOK3_AI = "book3_ai"  # fully AI under the constitution
BOOKS = (BOOK1_RULES, BOOK2_HYBRID, BOOK3_AI)
JOURNAL_FOLDER = "journal"
# Shadow versions (owner, 14 Oct 2026, experiment 2 option a): a research candidate's forward paper test runs in its own
# account `journal/shadow/<name>-v<n>/account/`, named `shadow:<name>-v<n>`, never in a book's account
SHADOW_FOLDER, SHADOW_PREFIX = "shadow", "shadow:"
# Kinds of row in a paper account's cash ledger (journal/<book>/account/cash_ledger.csv)
LEDGER_OPENING = "opening_balance"
LEDGER_FILL = "fill"
LEDGER_SETTLEMENT = "settlement"  # an option closed by NSE's cash settlement at expiry (story E7), not a trade
LEDGER_TOP_UP = "capital_top_up"  # capital added to a book at its write instant (story E1b; owner, 15 Oct 2026, "2 B")

# Order sides, one definition for the accounting ledgers, the charges model and the paper-account fills
SIDE_BUY, SIDE_SELL = "buy", "sell"
SIDES = (SIDE_BUY, SIDE_SELL)

# NSE participant-wise open interest (story A8, fno/research_data/participant_oi.py): who holds the contracts, and the
# instrument groups NSE splits them into
PARTICIPANT_CLIENT, PARTICIPANT_DII, PARTICIPANT_FII, PARTICIPANT_PRO = "Client", "DII", "FII", "Pro"
PARTICIPANTS = (PARTICIPANT_CLIENT, PARTICIPANT_DII, PARTICIPANT_FII, PARTICIPANT_PRO)
OI_FUTURE_INDEX, OI_FUTURE_STOCK = "future_index", "future_stock"
OI_OPTION_INDEX_CALL, OI_OPTION_INDEX_PUT = "option_index_call", "option_index_put"
OI_OPTION_STOCK_CALL, OI_OPTION_STOCK_PUT = "option_stock_call", "option_stock_put"
OI_GROUPS = (
    OI_FUTURE_INDEX, OI_FUTURE_STOCK, OI_OPTION_INDEX_CALL, OI_OPTION_INDEX_PUT, OI_OPTION_STOCK_CALL,
    OI_OPTION_STOCK_PUT,
)  # fmt: skip
# Outcomes of one release-time check of a published file (fno/research_data/release_times.py)
RELEASE_PRESENT, RELEASE_ABSENT, RELEASE_UNREACHABLE = "present", "absent", "unreachable"
RELEASE_REWRITTEN = "rewritten"  # present, but with other bytes than the first ones seen for that day

# NIFTY option-chain panel (story A3, fno/research_data/nifty_panel.py)
PANEL_FORMAT_UDIFF, PANEL_FORMAT_LEGACY = "udiff", "legacy"  # source_format: which F&O file a day's rows came from
PANEL_INDEX_CLOSE = "index-close"  # the index-close file of a day (underlying and India VIX)
# Why the daily panel job (story A13) cannot append a session yet
PANEL_FO_FILE_MISSING, PANEL_INDEX_CLOSE_MISSING = "fo_file_missing", "index_close_missing"
PANEL_INDEX_CLOSE_DIFFERS = "index_close_differs"
PANEL_DAY_OK, PANEL_DAY_NO_FILE, PANEL_DAY_NO_INDEX = "ok", "no file", "no index close"  # a day's status (manifest)
PANEL_DAY_FAILED = "failed"  # the day breaks the research-ready gate: the build fails, naming it
NIFTY_SYMBOL, INDEX_OPTION, INDEX_FUTURE = "NIFTY", "IDO", "IDF"  # F&O symbol; UDiFF codes of index options, futures
RECORDED_INDEX_OPTIONS = ("BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")  # 3 pm, after NIFTY (owner, 15 Oct 2026; A4c)

# Google Drive uploads as the owner (OAuth "Desktop app" client, one-time consent with tools/gdrive_oauth_setup.py);
# values only in the cloud environment's settings, never in files or chat. Service accounts cannot upload (no quota).
ENV_GDRIVE_OAUTH_CLIENT_ID = "FNO_GDRIVE_OAUTH_CLIENT_ID"
ENV_GDRIVE_OAUTH_CLIENT_SECRET = "FNO_GDRIVE_OAUTH_CLIENT_SECRET"
ENV_GDRIVE_OAUTH_REFRESH_TOKEN = "FNO_GDRIVE_OAUTH_REFRESH_TOKEN"
DRIVE_FULL_SCOPE = "https://www.googleapis.com/auth/drive"  # needed to add files inside the owner's existing folders

# Research features (story B1, fno/research_engine/): the names policies refer to, and when a day's close is known
FEATURE_ATM_IV_MINUS_RV20 = "F1_atm_iv_minus_rv20"  # ATM implied minus past 20-day realised volatility, in points
FEATURE_VIX_ABOVE_MEDIAN = "F2_vix_above_250d_median"  # India VIX close above its previous 250 closes' median
FEATURE_EVENT_IN_WINDOW = "F3_scheduled_event_in_window"  # a known scheduled event after entry, up to exit
SESSION_CLOSE_TIME = time(15, 30)  # IST: a regular or special session's closing prices exist from here
DESK_DECISION_TIME = time(15, 0)  # design 13.5: books decide at about 15:00 IST; story E3 freezes the exact timetable
OPTION_CALL, OPTION_PUT = "CE", "PE"

# Cycle simulator (story B2, fno/research_engine/): structure codes, as the experiment 1 protocol names them
STRUCTURE_SHORT_IRON_FLY, STRUCTURE_SHORT_CONDOR, STRUCTURE_LONG_IRON_FLY = "SF", "SC", "BF"
STRUCTURES = (STRUCTURE_SHORT_IRON_FLY, STRUCTURE_SHORT_CONDOR, STRUCTURE_LONG_IRON_FLY)
# One- and two-leg structures (story STR1), each anchored at the ATM strike: bought calls and puts, vertical spreads
STRUCTURE_LONG_CALL, STRUCTURE_LONG_PUT = "LC", "LP"
STRUCTURE_CALL_DEBIT_SPREAD, STRUCTURE_CALL_CREDIT_SPREAD = "CDS", "CCS"  # bull call and bear call spreads
STRUCTURE_PUT_DEBIT_SPREAD, STRUCTURE_PUT_CREDIT_SPREAD = "PDS", "PCS"  # bear put and bull put spreads
STRUCTURES_BOUGHT_ONLY = (STRUCTURE_LONG_CALL, STRUCTURE_LONG_PUT)  # no sold leg: width may be 0, margin may be 0
# Story STR1b: each open gate before an STR1 code may be used, and the uses it blocks. Removing a gate is a judged
# one-line change: STR1b-2 (E5/E7/E4 tests per code) removes its own; E8 (owner-timing fills) blocks paper use only.
USE_SHADOW, USE_PAPER = "shadow", "paper"
STR1_ACTIVATION_PENDING = {"STR1b-2": (USE_SHADOW, USE_PAPER), "E8": (USE_PAPER,)}
STRUCTURES_ONE_SIDE = (
    *STRUCTURES_BOUGHT_ONLY,
    STRUCTURE_CALL_DEBIT_SPREAD, STRUCTURE_CALL_CREDIT_SPREAD, STRUCTURE_PUT_DEBIT_SPREAD, STRUCTURE_PUT_CREDIT_SPREAD,
)  # fmt: skip


class CycleStatus(StrEnum):
    """Every outcome of one structure in one monthly cycle (story B2); story B3 consumes exactly these values."""

    TRADED = "traded"
    NO_TRADE_CAP = "no_trade_cap"  # every listed, priceable width breaks the Rs 10,000 cap
    MISSING_STRIKES = "missing_strikes"  # a data condition: no width has all its strikes listed on the entry day
    NO_ENTRY_WINDOW = "no_entry_window"  # the entry day is not before the exit day
    UNFILLABLE = "unfillable"  # a missing or zero price, or more than half the legs on settlement prices
    BAD_PRICES = "bad_prices"  # stale prices: a short credit at least the width, or a long debit at most zero


# Policy runner (story B3): the periods of an experiment, and an opportunity a policy chose not to trade
PERIOD_DISCOVERY, PERIOD_CHALLENGE = "discovery", "challenge"
NO_TRADE = "no_trade"

# Live 15:00 feature versions (story B7): different features from F1-F3, validated against them before use
FEATURE_ATM_IV_MINUS_RV20_LIVE = "F1_live_atm_iv_minus_rv20"
FEATURE_VIX_ABOVE_MEDIAN_LIVE = "F2_live_vix_above_250d_median"
FEATURE_EVENT_IN_WINDOW_LIVE = "F3_live_scheduled_event_in_window"
ENV_GITHUB_RUN_ID, ENV_GITHUB_RUN_ATTEMPT = "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"  # set by GitHub Actions (P7)
ENV_FNO_DB_URL = "FNO_DB_URL"  # the fno schema's runtime publisher role (stories P3, P6); environment settings only

# Risk manager (story C2, fno/risk/): the owner's restart entry for a book's drawdown brake, and the two frozen ways
# to stress a margin
CASH_LEDGER_FILE = "cash_ledger.csv"  # journal/<book>/account/cash_ledger.csv: E1's append-only ledger
OWNER_OVERRIDES_FILE = "owner_overrides.csv"  # journal/<book>/owner_overrides.csv, written by the owner only
DESK_DECISIONS_FILE = "docs/DESK_DECISIONS.md"  # the owner's decisions; a brake restart cites one row (story C5b)
BOOK_DISPLAY_NAMES = {BOOK1_RULES: "Book 1", BOOK2_HYBRID: "Book 2", BOOK3_AI: "Book 3"}  # as the owner writes them
OVERRIDE_RESTART_BRAKE = "restart_brake"
STRESSED_MARGIN_SCENARIO_LOOKUP, STRESSED_MARGIN_MULTIPLIER = "scenario_lookup", "multiplier"
STRESSED_MARGIN_METHODS = (STRESSED_MARGIN_SCENARIO_LOOKUP, STRESSED_MARGIN_MULTIPLIER)
STRESSED_MARGIN_STRESSES = "scan and exposure (owner, 15 Oct 2026; story C2c)"  # every decision record's label
# Story C2d: the stress factor k as A14c's weekly job appends it (append-only), read by C2 and by C4 with its own reader
STRESS_FACTOR_COLUMNS = (
    "as_of", "factor", "computed", "unrounded", "status", "peak", "coverage_through", "evidence_sha256",
)  # fmt: skip
STRESS_FACTOR_STATUSES = ("applied", "held")  # held: a lower result waits for the owner; the old factor stays in force
STRESS_FACTOR_DATE = "%Y-%m-%d"  # the only date form accepted in the factor file
# Risk buckets (story C5, design 6.2): an underlying group and a side of exposure. Only the index groups 6.2 names are
# mapped; a stock (its own group, or "stock results this week") is unmapped until the events calendar is wired in.
BUCKET_SHORT_VOL, BUCKET_LONG_VOL, BUCKET_BULLISH, BUCKET_BEARISH = (
    "short_volatility", "long_volatility", "bullish", "bearish",
)  # fmt: skip
BUCKET_SIDES = (BUCKET_SHORT_VOL, BUCKET_LONG_VOL, BUCKET_BULLISH, BUCKET_BEARISH)
BUCKET_INDEX_GROUPS = ("NIFTY", "BANKNIFTY")
# Risk profiles (story C5, config.yaml risk.profiles): the three paper books on the Rs 20 lakh account, and the Manual
# paper account on its 13 Oct 2026 limits (DESK_DECISIONS, 15 Oct 2026: "1 A", "2 A")
RISK_PROFILE_BOOKS, RISK_PROFILE_MANUAL = "books", "manual"

# Daily forecasts (epic G, research/forecasts/PROTOCOL.md): the five frozen questions and who answers them
FORECAST_Q1_UP_20D = "q1_nifty_up_20d"  # P(NIFTY close in 20 trading days > today's close)
FORECAST_Q2_MOVE_3PCT_20D = "q2_nifty_move_3pct_20d"  # P(|NIFTY return over 20 trading days| >= 3%)
FORECAST_Q3_RV_RISES_20D = "q3_rv20_above_trailing"  # P(next-20-day realised vol > trailing 20-day realised vol)
FORECAST_Q4_VIX_UP_10D = "q4_vix_up_10d"  # P(India VIX close in 10 trading days > today's close)
FORECAST_Q5_RV_BELOW_IV = "q5_rv20_below_atm_iv30"  # P(next-20-day realised vol < today's 30-day ATM IV)
FORECAST_QUESTIONS = (
    FORECAST_Q1_UP_20D, FORECAST_Q2_MOVE_3PCT_20D, FORECAST_Q3_RV_RISES_20D, FORECAST_Q4_VIX_UP_10D,
    FORECAST_Q5_RV_BELOW_IV,
)  # fmt: skip
BASELINE_RISK_NEUTRAL, BASELINE_BASE_RATE, BASELINE_MODEL = (
    "baseline_a_risk_neutral",
    "baseline_b_base_rate",
    "baseline_c_model",
)
FORECASTERS = BOOKS + (BASELINE_RISK_NEUTRAL, BASELINE_BASE_RATE, BASELINE_MODEL)

# Forecast protocol v4 (story G6, research/forecasts/PROTOCOL_v4.md): the movement-size questions, their forecaster
# slots and baselines. V6 is two targets (one session, five sessions).
V1_RV_1S, V2_RV_5S, V3_RV_20S = "v1_rv_next_session", "v2_rv_next_5_sessions", "v3_rv_next_20_sessions"
V4_RV_BELOW_WEEKLY_IV = "v4_rv5_below_weekly_atm_iv"  # probabilistic diagnostic
V5_INSIDE_STRADDLE = "v5_close_inside_k_plus_minus_p"  # terminal intrinsic-payoff proxy
V6_BIG_MOVE_1S, V6_BIG_MOVE_5S = "v6_abs_move_2pct_next_session", "v6_abs_move_2pct_within_5_sessions"
V7_VIX_UP_5S = "v7_vix_higher_in_5_sessions"
V4_QUESTIONS = (
    V1_RV_1S, V2_RV_5S, V3_RV_20S, V4_RV_BELOW_WEEKLY_IV, V5_INSIDE_STRADDLE, V6_BIG_MOVE_1S, V6_BIG_MOVE_5S,
    V7_VIX_UP_5S,
)  # fmt: skip
V4_SLOT_RULES, V4_SLOT_HYBRID, V4_SLOT_AI = "rules", "hybrid", "ai_team"  # one registered forecaster per slot
V4_SLOTS = (V4_SLOT_RULES, V4_SLOT_HYBRID, V4_SLOT_AI)
V4_DAY_A, V4_DAY_SYSTEM_LATE = "A", "system_late"  # G10: a day's quality label (protocol 1.6; A2 dropped, 16 Oct)
V4_COHORT_CLOSE_PROXY, V4_COHORT_LIVE = "close_proxy", "live"  # G10: scored apart, never pooled
V4_BASELINE_HAR_DAILY, V4_BASELINE_HAR_INTRADAY = "har_daily", "har_intraday"
V4_BASELINE_TRAILING, V4_BASELINE_EWMA = "trailing", "ewma_094"
V4_BASELINE_RAW_IMPLIED, V4_BASELINE_PREMIUM_ADJUSTED = "raw_implied", "premium_adjusted_implied"
V4_BASELINE_OPTION_IMPLIED_PROB, V4_BASELINE_BASE_RATE = "option_implied_probability", "base_rate"
V4_RULE_V6_EWMA_T4, V4_RULE_V1_CLOSE_BLEND = "v6_ewma_t4", "v1_close_blend"  # story G7
V4_IV30_EOD_PROXY = "iv30_eod_close_proxy"  # G1 v1's estimator on the panel's end-of-day chains (premium ratio window)
V4_CLAIM, V4_TOO_SMALL, V4_FUTILE, V4_OPEN = "claim", "real_but_too_small", "futile", "open"  # a member's verdict
STOP_YES, STOP_NO, STOP_UNDECIDED = "yes", "no", "undecided"  # design v2 section 8.2, tests A and B
STOP_NO_ECONOMIC_TEST = "undecided/no_economic_test"  # Test B with zero counted shadows
STOP_OR_PIVOT, CONTINUE_HALF_AI_BUDGET, CONTINUE = "stop_or_pivot", "continue_6_months_half_ai_budget", "continue"
UNDECIDED_OPTION_1, UNDECIDED_OPTION_2 = "option_1_continue_to_settle_date", "option_2_code_only"

# Company filings archive (story A12, fno/filings/): the filing types archived, and where NSE serves their files
FILING_RESULTS, FILING_SHAREHOLDING = "results-xbrl", "shareholding-xbrl"  # one XBRL file per filing
FILING_ANNOUNCEMENTS, FILING_BOARD_MEETINGS = "announcements", "board-meetings"  # one all-company list per day
FILING_FILE_KINDS = (FILING_RESULTS, FILING_SHAREHOLDING)
CONSOLIDATED, STANDALONE = "consolidated", "standalone"
NSE_FILINGS_FOLDER = "nse/equities/filings"  # archive folder of every NSE filing type

# Story O6: GitHub Actions fetch, then fire the Claude routine that reasons on the new data. One trigger ID and one
# bearer token per routine (made by the owner on the routine's web page, shown once); repository secrets only.
ENV_ROUTINE_DRY_RUN_TRIGGER_ID = "FNO_ROUTINE_DRY_RUN_TRIGGER_ID"
ENV_ROUTINE_DRY_RUN_TOKEN = "FNO_ROUTINE_DRY_RUN_TOKEN"
ROUTINE_DRY_RUN = "dry-run"  # the example reasoning routine: reads a pointer, writes a small derived summary
PIPELINE_AREA, DERIVED_AREA = "pipeline", "derived"  # Drive areas beside raw/ and revisions/ (fno/storage/README.md)

# Stories F1 and G5: the AI books' daily forecasts, one routine per book fired by the forecast-capture job
AI_BOOKS = (BOOK2_HYBRID, BOOK3_AI)
# Owner, 14 Oct 2026: the AI books' isolation for forecasts. The other AI book's same-day answer is sealed; the
# routine still has the public repository and network, so this is not full F1 isolation (trading needs that).
ISOLATION_SEALED_SAME_DAY = "sealed_same_day"
ENV_ROUTINE_BOOK2_TRIGGER_ID = "FNO_ROUTINE_BOOK2_HYBRID_TRIGGER_ID"
ENV_ROUTINE_BOOK2_TOKEN = "FNO_ROUTINE_BOOK2_HYBRID_TOKEN"
ENV_ROUTINE_BOOK3_TRIGGER_ID = "FNO_ROUTINE_BOOK3_AI_TRIGGER_ID"
ENV_ROUTINE_BOOK3_TOKEN = "FNO_ROUTINE_BOOK3_AI_TOKEN"
# Story LR1: the weekly post-mortem's one routine (AI summary, then objections), fired by its weekly job
ENV_ROUTINE_POSTMORTEM_TRIGGER_ID = "FNO_ROUTINE_POSTMORTEM_TRIGGER_ID"
ENV_ROUTINE_POSTMORTEM_TOKEN = "FNO_ROUTINE_POSTMORTEM_TOKEN"
ENV_GITHUB_TOKEN = "GITHUB_TOKEN"  # the Actions run's own token: reads the repository's push log (receipt times)
GITHUB_REPOSITORY_VARIABLE = "GITHUB_REPOSITORY"  # owner/name, set by GitHub Actions (not a secret, so no ENV_ name)
DEFAULT_REPOSITORY = "exepex/omenix-trading"  # outside GitHub Actions, where GITHUB_REPOSITORY is not set


# Playbook (story D1, fno/playbook/): a strategy version's lifecycle, who may change it, and its files
class PlaybookStatus(StrEnum):
    """A strategy version's state; the append-only registry's latest row decides it (owner: candidate = research,
    approved = paper)."""

    RESEARCH = "research"  # a candidate: never traded, not a passed strategy
    PAPER = "paper"  # approved: Book 1 may trade it on paper
    PAUSED = "paused"  # was paper; no new trades until the owner approves it again
    RETIRED = "retired"  # final


APPROVER_OWNER = "owner"
APPROVER_HARD_LOSS_RULE = "hard_loss_rule"  # the automatic pause of story E6 (paper -> paused only)
APPROVER_DESK = "desk"  # a builder or the research loop: may register a candidate (orchestrator, 14 Oct 2026)
PLAYBOOK_FOLDER = "playbook"
BOOK3_FOLDER = "book3"  # Book 3's constitution and strategy registry (story D5)
PACKS_FOLDER = "packs"  # journal/packs/<date>/common.json and journal/<book>/packs/<date>/private.json (story E2)
PLAYBOOK_REGISTRY_FILE = "registry.csv"
VALIDITY_FAILURES_FILE = "validity_failures.csv"  # journal/<book>/validity_failures.csv: C4's blocked trades
# Entry-condition operators: numbers compare with a number, flags with `is` and true or false
# Story D2: a strategy version with fewer completed paper trades than this is unproven and holds at most one open trade
UNPROVEN_BELOW_COMPLETED_TRADES, UNPROVEN_MAX_OPEN_TRADES = 20, 1
PAPER_GATE_MONTHS = 3  # design 6: with UNPROVEN_BELOW_COMPLETED_TRADES completed trades, the paper gate (E6 reviews)
NO_TRADE_THRESHOLD_RS = 0.0  # a candidate needs expected net per opportunity above this, after costs
NO_ESTIMATE = "none"  # a research version with no honest expected-net estimate (paper needs a number)


class Decision(StrEnum):
    """What story D2 decided for one opportunity."""

    CHOSEN = "chosen"  # allocated: the book opens this trade
    NOT_CHOSEN = "not chosen"  # a valid candidate that lost its slot, cash or risk check to the ranking
    NO_TRADE = "no trade"  # the rule did not fire, or no valid trade could be built
    SHADOW_TRADE = "shadow: would trade"  # a research candidate's forward test: recorded, never in the book
    SHADOW_NO_TRADE = "shadow: no trade"


EXPIRY_MONTHLY = "monthly"  # the only expiry kind a playbook names today (story D2)
OPERATOR_ABOVE, OPERATOR_AT_LEAST, OPERATOR_BELOW, OPERATOR_AT_MOST, OPERATOR_IS = ">", ">=", "<", "<=", "is"
NUMBER_OPERATORS = (OPERATOR_ABOVE, OPERATOR_AT_LEAST, OPERATOR_BELOW, OPERATOR_AT_MOST)

# Story E4: the paper fill model. What each desk fill did, and how an entry or exit attempt ended (desk_events.csv)
FILL_OPEN, FILL_UNWIND, FILL_CLOSE, FILL_SETTLE = "open", "unwind", "close", "settle"
OUTCOME_OPENED = "opened"
OUTCOME_REFUSED = "refused"  # a gate stopped it before any leg was priced (C2, timing, snapshot, a blocked book)
OUTCOME_NOT_OPENED = "not_opened"  # a leg did not fill (or the entry was worse than approved): nothing opened
OUTCOME_PARTIAL_FILL = "not_opened_partial_fill"  # a leg failed after others filled; the filled legs were unwound
OUTCOME_EXIT_ORDERED = "exit_ordered"  # an exit rule was reached (or an unwind could not finish): close at valid quotes
OUTCOME_PENDING_EXIT = "pending_exit"  # an exit leg had no valid quote: retried at the next scheduled snapshot
OUTCOME_CLOSED = "closed"
OUTCOME_PROTECTION_UNVERIFIED = "protection_unverified"  # a protective leg is unquotable: no new risk in the book
OUTCOME_SETTLEMENT_NEEDED = "settlement_needed"  # a leg expired before its exit filled: NSE's settlement price needed
# Story E8: an entry handed to the owner-timing fill (filled at the next session's due mark), and its views
OUTCOME_ENTRY_PENDING = "entry_pending"
VIEW_VERDICT, VERDICT_REACTION_MINUTES = "verdict", 60  # R = 60 is the verdict (DESK_DECISIONS row 181)
# Entry limit: the net entry at the execution snapshot's touch is worse than the entry C2 approved (its modelled cash)
ENTRY_WORSE_THAN_APPROVED = "entry_worse_than_approved"
# Story E4c: the entry check before any leg fills (every leg's opening side, a protective leg's closing side too)
PROTECTION_NOT_BUYABLE = "protection_not_buyable"
PROTECTION_NOT_SELLABLE = "protection_not_sellable"
SHORT_LEG_NOT_SELLABLE = "short_leg_not_sellable"
SIZE_SHARED_IN_BOOK = "size_shared_in_book"  # story E4d: the size covers this entry alone, not with the book's others
DATA_UNVERIFIED = "no new trade: stale or unverified data"  # story C3: a data check failed before the decision
NO_DECISION_LATE = "no decision (late)"  # story E3: nothing committed by the decision deadline
NO_APPROVED_STRATEGY = "no approved strategy"  # story E5: Book 1 has no `paper` version on the day

# Story E6: what a review date decides for a strategy version (per its evaluation plan)
REVIEW_KEEP, REVIEW_PAUSE, REVIEW_RETIRE = "keep", "pause", "retire"

# NSE margins (story A14, fno/nse_margins/): NSE Clearing's exposure (extreme-loss) margin on index options, from its
# equity-derivatives margins page (its daily `ael_DDMMYYYY.csv` lists stocks only), and when a day's
# beginning-of-day SPAN file must exist
INDEX_OPTION_EXPOSURE_RATE = 0.02  # of notional (underlying's last close x quantity), per short index option
DEEP_OTM_EXPOSURE_RATE, DEEP_OTM_DISTANCE = 0.03, 0.10  # a short option more than 10% out of the money
EXPOSURE_MODEL_MAX_MONTHS = 9  # beyond 9 months (5%) and on expiry day (+2%) NSE's rule differs: not modelled
SPAN_BOD_CREATED_BEFORE = time(9, 0)  # IST: a day's `i1` file must be written before this (point in time)
MARGIN_SOURCE_NSE_SPAN = "NSE SPAN"  # margins.csv `source` prefix of a computed row: "NSE SPAN <file> sha256=<hex>"


# The daily trade card (story T1, fno/cards/): its status, the reason codes of a `NO TRADE` card (design 04, 4.1),
# where its records go (Drive only, owner 15 Oct 2026) and the clock contract of design 04 section 4.4
class CardStatus(StrEnum):
    TRADE = "TRADE"
    NO_TRADE = "NO TRADE"
    WATCH = "WATCH"


CARD_NO_APPROVED_STRATEGY = "no_approved_strategy"  # no playbook version is at `paper`
CARD_TRADE_FIELDS_NOT_BUILT = "trade_fields_not_built"  # a version is at `paper`; card v1 has no trade fields (slice B)
CARD_DATA_CHECK_FAILED = "data_check_failed"  # a record the status needs could not be read
CARD_HARD_RULE_BREACH = "hard_rule_breach"  # T2: C4 refused a book's proposed trade today (its committed rows)
CARD_STEP_PROBLEMS = "step_problems"  # T1e: a desk step failed or was refused today (O1's `problem_steps`)
CARDS_AREA = "cards"  # Drive area of the card records (beside raw/ and pipeline/); never the public repository
PAPER_AREA = "paper"  # Drive area of the private paper records: accounts, desk records, private packs (story E2c)
DAILY_TOTALS_FILE = "daily_totals.csv"  # journal/<book>/daily_totals.csv: the public per-book daily totals (story E2c)
CARD_DELIVERIES_FOLDER = "research/cards/deliveries"  # non-sensitive delivery metadata only (no card text)
CARD_VALID_UNTIL = time(15, 25)  # IST: design 04 4.1, a card is valid until 15:25
CLOCK_SKEW_WARNING_SECONDS = 5.0  # design 04 4.4: host clock vs Slack's and GitHub's server times
CARD_SESSION_KINDS = (
    SESSION_REGULAR,
    SESSION_SPECIAL,
)  # a muhurat session is the one-hour Diwali session: no 15:00 card

ENV_GITHUB_OUTPUT = "GITHUB_OUTPUT"  # an Actions step's outputs file: the health check (O8) records that it posted

# Stories S1 and BR1a: the protocols `python -m fno evaluation check|freeze|verify --protocol` reads
PROTOCOL_EVALUATION, PROTOCOL_BREADTH = "evaluation", "breadth"
