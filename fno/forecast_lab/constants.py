"""Story FL1's fixed values and message templates (the channel IDs live in `fno/constants_channels.py`)."""

from __future__ import annotations

from datetime import time

UNDERLYINGS = ("NIFTY", "BANKNIFTY")  # owner, 21 Oct 2026 (DESK_DECISIONS row 262)
ISSUE_CLOSE = "1545"  # phase 1's one issue (owner, "Lab universe, report times and phasing")
HORIZON_SESSIONS = {"N1": 1, "N3": 3}  # sessions after the issue day; N0 comes with the 09:15 issue (FL1-2)
LEVELS = (0.05, 0.25, 0.50, 0.75, 0.95)
SEAL_BY = time(9, 15)  # a forecast counts for a target day only if sealed before that day's open
CALIBRATION_DAYS, EDGE_WINDOW = 60, "6-12 months"
MORNING, EVENING = "morning", "evening"  # the two editions (owner, DESK_DECISIONS lines 284 and 287; story FL1-1d)
COMMANDS = {MORNING: "lab open", EVENING: "lab close"}
REPORT_AREAS = {e: f"forecast_lab/v1/{e}" for e in (MORNING, EVENING)}  # under O9's Drive data area, per edition
MORNING_BY = SEAL_BY  # the morning edition is today's forecast only before the open: never posted at or after 09:15

HEADER = "F&O forecast lab {day}: evening report (paper research only, never an order)"
TRUST = (
    "Trust: {days} scored trading day(s) of about {needed} needed to judge calibration; a trading edge needs {edge}. "
    "One day's forecasts, of every contract, are one outcome, not many."
)
NO_ISSUE = "{underlying} {horizon} for {target} (issued {issue_day}): no forecast was sealed; nothing to score"
LATE = "{underlying} {horizon} for {target} (issued {issue_day}): sealed late ({sealed}); not shown as a forecast"
NONE_EXPECTED = "{underlying} forecasts for {target}: none expected (issued before G13b's first live day)"
SEALS_OK = "{underlying} forecasts for {target}: every one sealed in time"
NOT_IN_TIME = " {horizon}, issued {issue_day}: no forecast sealed in time (its seal check said why)"
SCORES_NOT_READY = (
    "{underlying}: the official close of {target} is archived but G13b has not scored all its forecasts yet; its match "
    "comes in a later report"
)
NOT_SEALED_YET = "{underlying} next sessions: today's 15:45 issue is not sealed yet; not shown"
MATCH_HEADER = (
    "{underlying} match: the forecasts for {target} against its official close; the latest days are matched in a "
    "later report (NSE archives the close in the evening)"
)  # owner, 21 Oct 2026 (DESK_DECISIONS): 15:45, the match lags one session, said in the report
NOT_ARCHIVED = "{underlying}: the official close of {target} is not archived yet; its match comes in a later report"
LOOKBACK_SESSIONS = 5  # a day not checked or matched yet is taken up by a later report within a week, then dropped
ALERT = "F&O forecast lab {day}: {what}"
NOT_A_SESSION = "{name} {day}: not a regular session; nothing posted"
ALREADY_POSTED = "{name} {day}: already posted and alerted; nothing sent again"
REPORT_POSTED = "{name} {day}: report to #fno-forecast: {outcome}"
REPORT_ALREADY = "{name} {day}: report already posted to #fno-forecast"
ALERTS_SENT = "{name} {day}: {sent} of {total} alert(s) sent to #fno-desk"
ALERTS_ALREADY = "{name} {day}: alerts already sent; none sent again"
NOT_POSTED = "the {edition} report was not posted to #fno-forecast ({outcome})"
CHECK_BEFORE_REPOST = "; check #fno-forecast before any repost"  # Slack may have posted it
NOT_LIVE = "{name} {day}: not live (config forecast_lab.live_from.{edition}: {since}); nothing posted"
TOO_LATE = "{name} {day}: not posted: it is {now:%H:%M}, and the morning edition is only posted before 09:15"
LATE_ALERT = "the morning edition was not posted before 09:15 (run at {now:%H:%M}); nothing was sent"
CRASHED = "the {edition} report was not made ({error}); nothing was posted"
