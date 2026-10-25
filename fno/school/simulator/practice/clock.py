"""The practice clock (story MS-SIM-d2): a session's decisions and fills happen at 15:30, the close the practice
snapshot is stamped with. Law 6 (MS-P1d) refuses a seal or a fill after the session's close, and a fill may not
precede its snapshot, so the only instant that satisfies both is the close itself. (The first ruling, 15:31, made
every practice fill a `stale_seal`; the orchestrator was told.) Fixed per session, as a replay's is."""

from datetime import date, datetime

from ....desk.settlement import SETTLEMENT_TIME as SESSION_CLOSE
from ....models import IST
from ...contracts.clock import FixedClock

PRACTICE_TIME = SESSION_CLOSE  # the snapshot is stamped here; law 6 refuses a fill after it
PRACTICE_CLOCK_LABEL = "practice clock 15:30 (closing prices)"


def practice_clock(session: date) -> FixedClock:
    return FixedClock(datetime.combine(session, PRACTICE_TIME, tzinfo=IST))
