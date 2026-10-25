"""What a report page shows (stories FL1-1c and FL1-1d, both editions), as plain values: the renderer draws it and
never computes a number, so the page and the text report cannot disagree about one."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .cues import Cue, SectionView


@dataclass(frozen=True)
class Band:
    """Index levels at the 5, 25, 50, 75 and 95% quantiles."""

    q05: float
    q25: float
    q50: float
    q75: float
    q95: float


@dataclass(frozen=True)
class RangeView:
    """Today's forecast for one horizon."""

    horizon: str  # "N1" or "N3"
    target_day: date
    band: Band
    p_up: float | None
    when: str = ""  # in words: "today", "tomorrow", "next trading day, Mon 26 Oct", "in 3 trading days, Wed 28 Oct"


@dataclass(frozen=True)
class Outcome:
    """One session on the timeline: its official close and the band the method had forecast for it."""

    day: date
    close: float
    band: Band
    inside_50: bool
    inside_90: bool
    live: bool  # a sealed live forecast; False for G13b's back-fill (history)
    provisional: bool = False  # the evening's own close (NSE's index list), until the official file confirms it
    gap_points: float = field(init=False)  # close minus the forecast's middle: the page shows it, never computes it
    gap_pct: float = field(init=False)  # the same gap as a percentage of the middle

    def __post_init__(self):
        object.__setattr__(self, "gap_points", round(self.close - self.band.q50, 2))
        object.__setattr__(self, "gap_pct", round((self.close - self.band.q50) / self.band.q50 * 100, 3))


@dataclass(frozen=True)
class Timeline:
    horizon: str
    method: str
    points: tuple[Outcome, ...]
    next_day: date | None = None  # today's forecast, drawn as the last segment (None when none was sealed)
    next_band: Band | None = None


@dataclass(frozen=True)
class Cell:
    """One method on one session: None when it had no scored forecast for that day."""

    day: date
    inside_50: bool | None
    inside_90: bool | None
    live: bool


@dataclass(frozen=True)
class Window:
    sessions: int  # the last n sessions
    count: int  # scored forecasts among them
    inside_50: float | None
    inside_90: float | None
    error_points: float | None  # mean quantile score in index points (lower is better)


@dataclass(frozen=True)
class MethodRecord:
    method: str
    cells: tuple[Cell, ...]  # oldest first, one per session on the grid
    windows: tuple[Window, ...]
    rolling_90: tuple[float | None, ...]  # 90% band coverage over the trailing 20 sessions, per grid session
    best: bool = False


@dataclass(frozen=True)
class Horizon:
    """One horizon of one index: its timeline, and every method's record on the same sessions."""

    timeline: Timeline
    methods: tuple[MethodRecord, ...]


@dataclass(frozen=True)
class Problem:
    """One drift or data problem: its index and horizon, the method (or "data") and what is wrong."""

    group: str  # "NIFTY next session"
    method: str
    text: str


@dataclass(frozen=True)
class Miss:
    """A recent session whose close fell outside "almost certainly", with its likely reasons (after the fact)."""

    day: date
    side: str  # "above" or "below"
    points: float  # how far outside the range
    reasons: tuple[str, ...]  # facts from our own data; "no clear reason in our data" when none


@dataclass(frozen=True)
class DayShape:
    """Today's path as NSE's index list gave it after 15:30 (A4h's read; measured, provisional like the close), and
    the previous session's official close. A level not recorded is None and is never shown (FL1-1f)."""

    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None


@dataclass(frozen=True)
class TrackRecord:
    """The next-session record, live and back-tested apart (owner, 23 Oct 2026): every live check so far (today's
    own included) and, for the light, the newest 30 live ones; the back-tested sessions among the last 30 sessions
    (judge E on FL1-1f: the label says what is counted)."""

    live_days: int
    live_right: int
    backtest_days: int
    backtest_right: int
    window: int = 30  # the sessions the back-test counts from (fewer while the history is shorter)
    live_recent_right: int = 0  # inside "almost certainly" among the newest 30 live checks: the light's count


CLOSE_NOT_READ, NO_FORECAST_TODAY = "close not read", "no forecast"  # `IndexView.unchecked` (FL1-1e)


@dataclass(frozen=True)
class IndexView:
    underlying: str
    price: float
    price_at: str
    method: str
    today: tuple[RangeView, ...]
    direction_edge: bool  # False while P(up) has shown no skill
    live_days: int
    days_needed: int
    horizons: tuple[Horizon, ...]  # N1 first
    right: int = 0  # of the last `scored` sessions, closes inside the "almost certainly" (90%) range, next session
    scored: int = 0
    misses: tuple[Miss, ...] = ()  # the last 30 sessions' misses, newest first
    light: str = "none"  # the 30-day light: "green", "amber", "red" or "none" (too few days)
    light_word: str = ""  # its word: "Good", "Watch", "Check" or "Too few live days to rate"
    wrong_days: tuple[date, ...] = ()  # of the last `scored` sessions, those outside "almost certainly", newest first
    backtested: int = 0  # of the last `scored` sessions, those scored on a back-fill, not a live sealed forecast
    why: tuple[Cue, ...] = ()  # the 2-4 key points (FL1-1d-2), in the stated order; context is never a cause
    levels: tuple[Cue, ...] = ()  # the evening's levels and flows table (FL1-1d-2)
    result: Outcome | None = None  # the edition's own check: today's (evening) or the previous session's (morning)
    unchecked: str = ""  # evening, no result: why today is not checked (CLOSE_NOT_READ or NO_FORECAST_TODAY)
    unchecked_why: str = ""  # its cause in words: the close reader's reason, or the issue that holds no forecast
    shape: DayShape | None = None  # evening, with a result: the day's path (FL1-1f)
    track: TrackRecord | None = None  # the record, live and back-tested apart (FL1-1f)


@dataclass(frozen=True)
class PageView:
    day: date
    provenance: str  # "Live, sealed" or a preview's label; always shown at the top
    indices: tuple[IndexView, ...]
    drift: tuple[Problem, ...]  # every method's accuracy check that failed (the details page only)
    system: tuple[str, ...] = field(default=())  # system problems (data late, a forecast missing): the message's line
    checks: tuple[str, ...] = field(default=())  # seal and coverage lines
    alerts: tuple[str, ...] = field(default=())
    edition: str = "evening"  # "morning" (today's forecast, 08:50) or "evening" (was it right, 20:05): FL1-1d
    confirmation: tuple[str, ...] = field(default=())  # morning: the last evening's close confirmed, or corrected
    cues: tuple[SectionView, ...] = field(default=())  # every Section in its one state (FL1-1d-2)
    next_session: date | None = None  # the next regular session: its morning report confirms today (FL1-1e)
