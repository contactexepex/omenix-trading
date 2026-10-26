"""Shared names and fixed strings. Change a value here, not where it is used."""

from __future__ import annotations

from datetime import time

from fno.shared.constants_channels import *  # noqa: F403 - story FL1's two channels; callers keep `fno.shared.constants`

# A daily run step's status, read by the ingestion feed gate (fno/ingestion/intraday/feed_gate.py)
STEP_OK = "ok"

# Environment variable names (values are never stored in files).
# Groww Trade API (market data only; the tool never places orders)
ENV_GROWW_ACCESS_TOKEN = "GROWW_ACCESS_TOKEN"
ENV_GROWW_API_KEY = "GROWW_API_KEY"
ENV_GROWW_API_SECRET = "GROWW_API_SECRET"
ENV_GROWW_TOTP_SECRET = "GROWW_TOTP_SECRET"
# Raw-file archive on Google Drive (fno/ingestion/storage): read-only service account; both only in the environment
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

# NSE session calendar (fno/ingestion/research_data/calendar.py): kinds of rows in nse_sessions.csv, and of sessions
SESSION_HOLIDAY, SESSION_SPECIAL, SESSION_MUHURAT, SESSION_REGULAR = "holiday", "special", "muhurat", "regular"

# Index names in NSE's daily index-close file that every file must carry (the research needs both)
INDEX_NIFTY_50, INDEX_INDIA_VIX = "Nifty 50", "India VIX"

# NSE participant-wise open interest (story A8, fno/ingestion/research_data/participant_oi.py): who holds the
# contracts, and the instrument groups NSE splits them into
PARTICIPANT_CLIENT, PARTICIPANT_DII, PARTICIPANT_FII, PARTICIPANT_PRO = "Client", "DII", "FII", "Pro"
PARTICIPANTS = (PARTICIPANT_CLIENT, PARTICIPANT_DII, PARTICIPANT_FII, PARTICIPANT_PRO)
OI_FUTURE_INDEX, OI_FUTURE_STOCK = "future_index", "future_stock"
OI_OPTION_INDEX_CALL, OI_OPTION_INDEX_PUT = "option_index_call", "option_index_put"
OI_OPTION_STOCK_CALL, OI_OPTION_STOCK_PUT = "option_stock_call", "option_stock_put"
OI_GROUPS = (
    OI_FUTURE_INDEX, OI_FUTURE_STOCK, OI_OPTION_INDEX_CALL, OI_OPTION_INDEX_PUT, OI_OPTION_STOCK_CALL,
    OI_OPTION_STOCK_PUT,
)  # fmt: skip
# Outcomes of one release-time check of a published file (fno/ingestion/research_data/release_times.py)
RELEASE_PRESENT, RELEASE_ABSENT, RELEASE_UNREACHABLE = "present", "absent", "unreachable"
RELEASE_REWRITTEN = "rewritten"  # present, but with other bytes than the first ones seen for that day

# NIFTY index-close file of a day (underlying and India VIX), by source format (fno/ingestion/pipeline)
PANEL_INDEX_CLOSE = "index-close"
NIFTY_SYMBOL = "NIFTY"  # F&O symbol
RECORDED_INDEX_OPTIONS = ("BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")  # 3 pm, after NIFTY (owner, 15 Oct 2026; A4c)

# Google Drive uploads as the owner (OAuth "Desktop app" client, one-time consent with ops/gdrive_oauth_setup.py);
# values only in the cloud environment's settings, never in files or chat. Service accounts cannot upload (no quota).
ENV_GDRIVE_OAUTH_CLIENT_ID = "FNO_GDRIVE_OAUTH_CLIENT_ID"
ENV_GDRIVE_OAUTH_CLIENT_SECRET = "FNO_GDRIVE_OAUTH_CLIENT_SECRET"
ENV_GDRIVE_OAUTH_REFRESH_TOKEN = "FNO_GDRIVE_OAUTH_REFRESH_TOKEN"

DESK_DECISION_TIME = time(15, 0)  # IST: data availability is judged as of about 15:00 IST

ENV_GITHUB_RUN_ID, ENV_GITHUB_RUN_ATTEMPT = "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"  # set by GitHub Actions (P7)
ENV_FNO_DB_URL = "FNO_DB_URL"  # the fno schema's runtime publisher role (stories P3, P6); environment settings only

# Company filings archive (story A12, fno/ingestion/filings/): the filing types archived, and where NSE serves them
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
PIPELINE_AREA, DERIVED_AREA = "pipeline", "derived"  # Drive areas beside raw/ and revisions/ (fno/ingestion/storage)

# Stories F1 and G5: the AI books' daily-forecast routines, each with its own trigger and token (repository secrets).
# The forecast layer is gone, but the record scan still watches these secret names (secret_env_names).
ENV_ROUTINE_BOOK2_TRIGGER_ID = "FNO_ROUTINE_BOOK2_HYBRID_TRIGGER_ID"
ENV_ROUTINE_BOOK2_TOKEN = "FNO_ROUTINE_BOOK2_HYBRID_TOKEN"
ENV_ROUTINE_BOOK3_TRIGGER_ID = "FNO_ROUTINE_BOOK3_AI_TRIGGER_ID"
ENV_ROUTINE_BOOK3_TOKEN = "FNO_ROUTINE_BOOK3_AI_TOKEN"
# Story LR1: the weekly post-mortem's one routine (AI summary, then objections), fired by its weekly job
ENV_ROUTINE_POSTMORTEM_TRIGGER_ID = "FNO_ROUTINE_POSTMORTEM_TRIGGER_ID"
ENV_ROUTINE_POSTMORTEM_TOKEN = "FNO_ROUTINE_POSTMORTEM_TOKEN"
ENV_GITHUB_TOKEN = "GITHUB_TOKEN"  # the Actions run's own token: reads the repository's push log (receipt times)
GITHUB_REPOSITORY_VARIABLE = "GITHUB_REPOSITORY"  # owner/name, set by GitHub Actions (not a secret, so no ENV_ name)
DEFAULT_REPOSITORY = "exepex/omenix-ingestion"  # outside GitHub Actions, where GITHUB_REPOSITORY is not set

ENV_GITHUB_OUTPUT = "GITHUB_OUTPUT"  # an Actions step's outputs file: the health check (O8) records that it posted

# Design 04 4.4: host clock vs Slack's and GitHub's server times (fno/shared/server_clock.py)
CLOCK_SKEW_WARNING_SECONDS = 5.0

# Story R1b2: a pause on a host is remembered between runs. A run reads the committed log and appends to the run-local,
# git-ignored one; the last workflow step merges the run-local rows into the committed file.
PAUSE_LOG_PATH = "research/data/resilience/paced-hosts.csv"
PAUSE_LOG_RUN_PATH = "research/data/resilience/.run/paced-hosts.csv"
# A command is live when its source overwrites in place or shows only the current value within the window the next run
# would read it, so a missed run cannot be redone: it keeps its one attempt even inside a carried-over cool-down.
# Spelled as the command words after `fno` (`fno quotes record`). A static test pins the set.
LIVE_WINDOW_COMMANDS = frozenset({
    "quotes record",
    "participant-oi watch",
    "participant-oi check-once",
    "closes read",
    "preopen record",
    "fo-masters",
    "data-snapshot fii-dii-cash-by-session",
    "data-snapshot fpi-daily-by-session",
})  # fmt: skip
