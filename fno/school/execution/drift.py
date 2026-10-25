"""The NIFTY drift diagnostic (story 3.6), never a fill: each filled NIFTY leg's touch at the decision snapshot against
the same contract's same-side touch in E3's 15:15 capture, so the optimism of "no latency" is measured. A leg the
15:15 capture lacks, or holds without a usable quote by A4's rule, gives `drift_unknown` (no number), never a guess."""

from datetime import date

from ...desk.snapshot import ExecutionSnapshot
from ..constants import RoadCode
from ..contracts.accounts import FilledLeg, FillResult
from ..contracts.records import DriftRow

NIFTY_ROADS = (RoadCode.NIFTY_MONTHLY, RoadCode.NIFTY_WEEKLY)


def drift_rows(session: date, position_id: str, road: RoadCode, fill: FillResult,
               capture_1515: ExecutionSnapshot | None) -> tuple[DriftRow, ...]:  # fmt: skip
    """One row per leg of a NIFTY road's entry or exit fill at the session's slot; none for another index (only NIFTY
    has a 15:15 capture). A settlement is not a touch: callers pass entry and exit fills only."""
    if road not in NIFTY_ROADS or not fill.filled:
        return ()
    if capture_1515 is not None and capture_1515.day != session:
        raise ValueError(f"the 15:15 capture {capture_1515.snapshot_id} is not of {session}")
    return tuple(DriftRow(session, position_id, leg, _touch_1515(capture_1515, leg)) for leg in fill.legs)


def _touch_1515(capture: ExecutionSnapshot | None, leg: FilledLeg) -> float | None:
    quote = None if capture is None else capture.quote(leg.key.expiry, leg.key.strike, str(leg.key.kind))
    if quote is None or quote.a4_problem:
        return None
    price, _ = quote.touch(leg.side)
    return price
