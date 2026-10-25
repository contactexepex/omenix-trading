"""The report in plain words (story FL1-1c v3; owner, 21 Oct 2026, DESK_DECISIONS 194aa8b3): the 3 Slack lines and
the words the picture uses. "Most likely" is the 50% range and "almost certainly" the 90% range; percentages and
method names stay in the details. "Right" means the next-session close fell inside "almost certainly"; the light is
green at 25 or more of the last 30 sessions, amber at 24, red at 23 or fewer (a method right 9 days in 10 falls to 23
or fewer by chance about 3% of the time: exact binomial). Ranges are rounded outward to the nearest 10 points, so
the words never claim a narrower range than the forecast. The evening answers its title first, per index (owner, 23
Oct 2026, FL1-1e): today's close and whether it fell inside each range, or why today is not checked yet, and when
it will be; the 30-day record is labelled as the past 30 days, back-tested days counted."""

from __future__ import annotations

import math
from datetime import date

from .model import CLOSE_NOT_READ, NO_FORECAST_TODAY, Band, IndexView, PageView, TrackRecord

STEP = 10  # points: ranges in words are rounded outward to this
WINDOW, GREEN_FROM, AMBER_AT = 30, 25, 24
LIGHTS = {"green": "🟢", "amber": "🟡", "red": "🔴", "none": "⚪"}
LIGHT_WORDS = {"green": "Good", "amber": "Watch", "red": "Check", "none": "Too few live days to rate"}
RESEARCH = "Research only. Not a trade tip."
NORMAL = "✅ All systems normal."
EDITIONS = {"morning": ("Today's forecast", "08:50"), "evening": ("Was today's forecast right?", "20:05")}
RESULTS = {(True, True): "✓ Correct", (False, True): "⚠ Close call", (False, False): "✗ Missed"}  # the designer's words
RIGHT = "Right = the close fell inside the “almost certainly” range."
YES_NO = {True: "yes", False: "no"}
VERDICTS = {True: "✓ right", False: "✗ wrong"}  # by `inside_90`, as RIGHT defines it (the designer's page reads both)
PROVISIONAL = "NSE's close; the official file confirms it in {report}"
OFFICIAL = "NSE's official close; G13b's score follows"
UNCHECKED = {
    CLOSE_NOT_READ: "today: not checked yet (NSE close not read); result in {report}",
    NO_FORECAST_TODAY: "today: not checked (no forecast was issued for today)",
}


def day_short(day: date) -> str:
    return f"{day:%a} {day.day} {day:%b}"


def when(ahead: int, target: date, today: date) -> str:
    """`ahead`: regular sessions from `today` to `target` (0: today). "tomorrow" only when the next session is the next
    calendar day; otherwise the day, so a holiday or a weekend never makes "tomorrow" wrong."""
    if ahead == 0:
        return "today"
    if ahead == 1 and (target - today).days == 1:
        return "tomorrow"
    words = "next trading day" if ahead == 1 else f"in {ahead} trading days"
    return f"{words}, {day_short(target)}"


def morning_report(today: date, next_session: date | None) -> str:
    """The morning report that confirms `today`: the next regular session's ("Monday's" after a Friday)."""
    if next_session is None:
        return "the next morning report"
    return "tomorrow's morning report" if (next_session - today).days == 1 else f"{next_session:%A}'s morning report"


def outward(low: float, high: float) -> tuple[int, int]:
    return math.floor(low / STEP) * STEP, math.ceil(high / STEP) * STEP


def likely(band: Band) -> str:
    low, high = outward(band.q25, band.q75)
    return f"{low:,}–{high:,}"


def certain(band: Band) -> str:
    low, high = outward(band.q05, band.q95)
    return f"{low:,}–{high:,}"


def light(index: IndexView) -> str:
    """Rated on live checks only once the page has its record (judge E on FL1-1f: back-tested days never colour it),
    over the newest 30; with fewer, "none" ("too few live days to rate")."""
    if index.track is not None:
        right, days = index.track.live_recent_right, min(index.track.live_days, WINDOW)
    else:
        right, days = index.right, index.scored
    if days < WINDOW:
        return "none"
    return "green" if right >= GREEN_FROM else "amber" if right == AMBER_AT else "red"


def light_words(index: IndexView) -> str:
    """The light before the record: its glyph, and the words when it cannot rate yet."""
    state = light(index)
    return f"{LIGHTS[state]} {LIGHT_WORDS[state].lower()} |" if state == "none" and index.track else LIGHTS[state]


def record_words(index: IndexView) -> str:
    """The record: live and back-tested apart when the page has them (FL1-1f), else the 30-day count."""
    if index.track is not None:
        return _track_words(index.track)
    if index.scored == 0:
        return "no scored days yet"
    tested = f" (back-tested {index.backtested})" if index.backtested else ""  # judge 434: never passed off as live
    return f"past {index.scored} days{tested}: inside “almost certainly” {index.right} of {index.scored}"


def _track_words(track: TrackRecord) -> str:
    days = f"{track.live_days} day{'s' if track.live_days != 1 else ''}"
    live = (f"Live so far: {days}, inside “almost certainly” {track.live_right} of {track.live_days}"
            if track.live_days else "Live so far: none scored yet")  # fmt: skip
    return f"{live} | {_backtest_words(track)}"


def _backtest_words(track: TrackRecord) -> str:
    """The back-tested sessions among the last `window` sessions, the label saying exactly that (judge E)."""
    if not track.backtest_days:
        return f"Back-test: none in the last {track.window} days" if track.window else "Back-test: none"
    whole = track.backtest_days == track.window
    which = f"last {track.window} days" if whole else f"{track.backtest_days} of the last {track.window} days"
    return f"Back-test ({which}): {track.backtest_right} of {track.backtest_days}"


def result_words(index: IndexView, today: date, next_session: date | None = None) -> str:
    """The edition's own check (today's in the evening, the previous session's in the morning), why today is not
    checked, or "" when neither."""
    result = index.result
    if result is None:
        return UNCHECKED[index.unchecked].format(report=morning_report(today, next_session)) if index.unchecked else ""
    when = "today" if result.day == today else day_short(result.day)
    label = PROVISIONAL.format(report=morning_report(today, next_session)) if result.provisional else OFFICIAL
    return (f"{when}: closed {result.close:,.2f} ({label}) · inside “most likely”: {YES_NO[result.inside_50]} · "
            f"inside “almost certainly”: {YES_NO[result.inside_90]} → {VERDICTS[result.inside_90]}")  # fmt: skip


def forecast_words(index: IndexView) -> list[str]:
    return [f"{view.when}: most likely {likely(view.band)} (almost certainly {certain(view.band)})"
            for view in index.today]  # fmt: skip


def index_line(index: IndexView, today: date, next_session: date | None = None) -> str:
    result = result_words(index, today, next_session)
    parts = [f"*{index.underlying}*", *([result] if result else []), *forecast_words(index)]
    return " · ".join(parts) + f" · {light_words(index)} {record_words(index)}"


def status_line(view: PageView) -> str:
    head = " ".join(f"⚠️ {problem.rstrip('.')}." for problem in view.system) if view.system else NORMAL
    return f"{head} {RESEARCH}"
