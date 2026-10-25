"""What makes a recorded capture usable (story 3.5), as pure rules the road catalogue and the quality gate share, so a
rule has one definition. Nothing here reads a store or a clock."""

from datetime import date, datetime, timedelta

from ...models import IST
from ...quotes.indices import INDEX_WINDOW_END, INDEX_WINDOW_START
from ...quotes.recorder import WINDOW_END, WINDOW_START
from ..constants import ClosureReason, RoadCode

# The recorder windows (A4 for NIFTY's monthly, A4c for the other indices and the NIFTY weekly, A4f): an attempt starts
# inside its window, so a canonical capture that started outside it was not taken by the recorder's own rule.
_NIFTY_WINDOW = (WINDOW_START, WINDOW_END)
_INDEX_WINDOW = (INDEX_WINDOW_START, INDEX_WINDOW_END)
CAPTURE_WINDOWS = {
    RoadCode.NIFTY_MONTHLY: _NIFTY_WINDOW,
    RoadCode.BANKNIFTY_MONTHLY: _INDEX_WINDOW,
    RoadCode.FINNIFTY_MONTHLY: _INDEX_WINDOW,
    RoadCode.MIDCPNIFTY_MONTHLY: _INDEX_WINDOW,
    RoadCode.NIFTY_WEEKLY: _INDEX_WINDOW,
}


WINDOW_GRACE_SECONDS = 60  # an attempt the recorder admitted at the window's last instant may stamp itself just after


def _end_with_grace(end):
    return (datetime.combine(date.min, end) + timedelta(seconds=WINDOW_GRACE_SECONDS)).time()


def window_problem(road: RoadCode, session: date, started_at: datetime, finished_at: datetime) -> ClosureReason | None:
    """`out_of_window` unless the capture started inside its road's recorder window on the session day and finished on
    that day. Times are compared in IST whatever zone the sidecar wrote."""
    start, end = CAPTURE_WINDOWS[road]
    began, ended = started_at.astimezone(IST), finished_at.astimezone(IST)
    inside = start <= began.time() <= _end_with_grace(end) and began.date() == session and ended.date() == session
    return None if inside else ClosureReason.OUT_OF_WINDOW


def expiry_problem(actual: tuple[date, ...], expected: tuple[date, ...]) -> ClosureReason | None:
    """`expiry_mismatch` unless the capture holds exactly the expiries the listing says its road records."""
    return None if tuple(actual) == tuple(expected) else ClosureReason.EXPIRY_MISMATCH
