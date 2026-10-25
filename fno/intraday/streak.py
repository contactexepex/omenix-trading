"""The alert after two bad snapshots in a row (story A16): a SYSTEM alert (design 6.5), first line saying what to do.

- One per streak: a streak (two or more bad marks in a row) is covered once an alert was SENT during or after it.
- At most one an hour: a streak found less than 60 minutes after the last sent alert is held, and sent at the first
  settlement after the hour, even if the streak has ended by then.
- A failed send (no Slack token, Slack down) does not count: it is retried at the next settlement.
The outcome line and its time are kept in the newest ledger row written with it."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..alerts.sender import SENT
from .document import parse_time
from .status import GOOD, INCOMPLETE

STREAK_LENGTH = 2
ALERT_GAP = timedelta(hours=1)
STREAK_ALERT = (
    "Action: check the 15-minute recorder ({check}). SYSTEM, story A16: {count} bad snapshots in a row on {day}: "
    "{marks}. {effect}"
)
CHECK_RUNNING = "is its routine running, does Groww sign in?"
CHECK_QUOTES = "are two runs taking one mark, is Groww limiting the rate?"
EFFECT_VOID = "Gaps stay gaps; this session's realised variance will be void."
# an incomplete mark has a usable index level (status.verdict): the realised variance needs only the index
EFFECT_QUOTES = "The index levels were usable, so the realised variance is not affected; contract quotes are missing."


def streak_alert_text(rows: list[dict], now: datetime) -> str:
    """The alert due now for the ledger's rows in mark order, or empty when none is due."""
    sent = [row for row in rows if SENT in row["alert"]]
    if sent and now - parse_time(sent[-1]["alert_at"]) < ALERT_GAP:
        return ""
    covered_to = sent[-1]["mark"] if sent else ""
    open_streaks = [s for s in _streaks(rows) if s[-1]["mark"] > covered_to and s[0]["mark"] > _start_of(rows, sent)]
    if not open_streaks:
        return ""
    streak = open_streaks[-1]
    marks = ", ".join(f"{r['mark_ist']} {r['status']} ({r['failures']})" for r in streak)
    quotes_only = all(r["status"] == INCOMPLETE for r in streak)
    check, effect = (CHECK_QUOTES, EFFECT_QUOTES) if quotes_only else (CHECK_RUNNING, EFFECT_VOID)
    return STREAK_ALERT.format(check=check, count=len(streak), day=streak[-1]["session"], marks=marks, effect=effect)


def _streaks(rows: list[dict]) -> list[list[dict]]:
    """Every run of at least two bad rows in a row."""
    found, current = [], []
    for row in rows + [{"status": GOOD}]:
        if row["status"] != GOOD:
            current.append(row)
            continue
        if len(current) >= STREAK_LENGTH:
            found.append(current)
        current = []
    return found


def _start_of(rows: list[dict], sent: list[dict]) -> str:
    """The first mark of the streak the last sent alert was raised in: that streak is covered as it goes on."""
    if not sent:
        return ""
    position = rows.index(sent[-1])
    while position > 0 and rows[position - 1]["status"] != GOOD:
        position -= 1
    return rows[position]["mark"]
