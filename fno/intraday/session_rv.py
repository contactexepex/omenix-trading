"""Computes a finished session's realised variance from the snapshots stored in Drive (story A16): each mark's copy is
the one its ledger row names, its index level is judged by the same rule as when it was taken
(`status.index_check`), the strategy computes the figure, and the row is written once. Also reports the share of void
sessions (design 5.2: above 5%, a new version is proposed). The same readings give protocol v4's moved-after-cutoff flag
and its sign (G10; `cutoff`, injected by the composition root), never a level."""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime, time

from ..models import now_ist
from ..quotes.recorder import RECORDED_SESSION_KINDS
from ..research_data.calendar import SessionCalendar
from .document import SnapshotDocument, utc_text
from .realised_vol import IntradayRealisedVol, RvResult
from .rv_table import RvTable
from .slots import label, marks
from .snapshot_files import SnapshotFiles
from .status import index_check

VOID_SHARE_LIMIT = 0.05
OK, VOID = "ok", "void"
VOID_SHARE_LINE = "void sessions: {void} of {total} ({share:.1%}){flag}"
NOT_COUNTED = "; not counted: {n} before the first session with a recorded previous session (void by construction)"
VOID_SHARE_FLAG = " - above 5%: propose a new version (design 5.2)"


def no_cutoff_flag(levels: dict[time, float | None]) -> tuple[str, str]:
    return "", ""


class SessionRv:
    def __init__(self, files: SnapshotFiles, calendar: SessionCalendar, table: RvTable,
                 strategy: IntradayRealisedVol, now: Callable[[], datetime] = now_ist,
                 cutoff: Callable[[dict[time, float | None]], tuple[str, str]] = no_cutoff_flag):  # fmt: skip
        self.files, self.source, self.calendar, self.table = files, files.source, calendar, table
        self.strategy, self.now, self.cutoff = strategy, now, cutoff

    def compute(self, day: date) -> str:
        """Writes the session's row (once) and returns a one-line outcome."""
        readings = self._readings(day, marks(day))
        previous_day = previous_recorded_session(self.calendar, day)
        closing = self._readings(previous_day, marks(previous_day)[-1:])
        result = self.strategy.compute([level for level, _, _ in readings], closing[0][0])
        row = self._row(day, result, readings + closing)
        levels = {mark.time(): level for mark, (level, _, _) in zip(marks(day), readings, strict=True)}
        row["moved_after_cutoff"], row["cutoff_move_sign"] = self.cutoff(levels)  # usable levels by mark (IST)
        outcome = self.table.write_once(row)
        shown = f"RV {row['rv_session']} (vol {row['vol_pct']}%)" if row["status"] == OK else row["void_reason"]
        return f"{day} realised variance {outcome}: {row['status']}, {shown}"

    def has_row(self, day: date) -> bool:
        return any(row["session"] == day.isoformat() for row in self.table.rows())

    def void_share_line(self) -> str:
        """The 5% rule's count starts at the first session whose previous recorded session has a row (owner, 16 Oct
        2026): before it the overnight part cannot exist, so those sessions are void by construction, listed apart."""
        rows = sorted(self.table.rows(), key=lambda r: r["session"])
        held = {r["session"] for r in rows}
        start = next((i for i, r in enumerate(rows) if self._previous_held(r["session"], held)), len(rows))
        counted = rows[start:]
        void = sum(1 for r in counted if r["status"] == VOID)
        share = void / len(counted) if counted else 0.0
        flag = VOID_SHARE_FLAG if share > VOID_SHARE_LIMIT else ""
        line = VOID_SHARE_LINE.format(void=void, total=len(counted), share=share, flag=flag)
        return line + (NOT_COUNTED.format(n=start) if start else "")

    def _previous_held(self, session: str, held: set[str]) -> bool:
        return previous_recorded_session(self.calendar, date.fromisoformat(session)).isoformat() in held

    def _readings(self, day: date, wanted: list[datetime]) -> list[tuple[float | None, str, str]]:
        """Per wanted mark: its usable level (None where missing or unusable), the basis of that level, and the stored
        file's SHA-256 ("" when there is none). Each mark's copy is the one its ledger row names."""
        found = []
        for mark in wanted:
            data = self.files.read(self.files.used(day, mark))
            doc = SnapshotDocument.from_bytes(data) if data else None
            level = index_check(doc).level if doc else None
            found.append((level, doc.index_basis if level is not None else "", _sha256(data)))
        return found

    def _row(self, day: date, result: RvResult, readings: list[tuple[float | None, str, str]]) -> dict:
        session_marks = marks(day)
        unusable = [label(session_marks[i]) for i in result.unusable_marks]
        reasons = ([f"no usable index level at {', '.join(unusable)}"] if unusable else []) + (
            ["no usable 15:30 level for the previous session"] if result.previous_close_missing else []
        )
        return {
            "session": day.isoformat(), "status": OK if result.session is not None else VOID,
            "rv_session": figure(result.session), "rv_intraday": figure(result.intraday),
            "rv_overnight": figure(result.overnight),
            "vol_pct": "" if result.vol_pct is None else f"{result.vol_pct:.4f}", "void_reason": "; ".join(reasons),
            "good_slots": len(session_marks) - len(unusable), "due_slots": len(session_marks),
            "basis_counts": _basis_counts(readings[: len(session_marks)]),
            "measure": self.strategy.measure, "method": self.strategy.method, "source": self.source,
            "as_of": utc_text(session_marks[-1]), "first_seen_at": utc_text(self.now()),
            "inputs_sha256": hashlib.sha256("\n".join(sha for _, _, sha in readings).encode()).hexdigest(),
        }  # fmt: skip


def previous_recorded_session(calendar: SessionCalendar, day: date) -> date:
    """The session before `day` whose 15:30 level the overnight return starts from: the previous regular or special
    session (a muhurat evening hour has no 15:30 mark; its move falls inside the next overnight return)."""
    previous = calendar.previous_session(day)
    while calendar.session_kind(previous) not in RECORDED_SESSION_KINDS:
        previous = calendar.previous_session(previous)
    return previous


def _basis_counts(readings: list[tuple[float | None, str, str]]) -> str:
    """How many usable levels each rule gave, e.g. `candle_1m_close:26` (a session mixing rules is visible)."""
    counts = Counter(basis for level, basis, _ in readings if level is not None)
    return ";".join(f"{basis}:{count}" for basis, count in sorted(counts.items()))


def _sha256(data: bytes | None) -> str:
    return hashlib.sha256(data).hexdigest() if data else ""


def figure(value: float | None) -> str:
    return "" if value is None else f"{value:.10f}"
