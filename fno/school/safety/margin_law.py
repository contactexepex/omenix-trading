"""Law 3's margin room (story 3.3; story section 6 item 7, revised; MS-P1m): C2's `MarginRoom`, unedited, on MS-P1m's
margin per trade (`fno/nse_margins/road_margin.py`: each trade's own legs, lot and index, from the session's archived
beginning-of-day SPAN file, SEBI's extra exposure on an expiring trade's own expiry day). Any trade of the check (the
proposal or a held one) whose margin cannot be read is refused (`margin_room`), fail closed, with the note
"margin not checked: <the named cause>"; a margin is never guessed."""

from collections.abc import Mapping

from ...risk.margins import StressedMargin
from ...risk.rules import MarginRoom
from ...risk.trade_costs import TradeCosts
from ..constants import RefusalReason, RoadCode
from ..contracts.safety import LawResult
from ..contracts.snapshot import SlotSnapshot
from .c2_laws import C2Law, margin_numbers

MARGIN_ROOM = "margin_room"
MARGIN_NOT_CHECKED = "margin not checked: "  # then MS-P1m's or C2's own reason


def margin_room_law(margin: StressedMargin, costs: TradeCosts, slot: Mapping[RoadCode, SlotSnapshot]) -> C2Law:
    return C2Law(MARGIN_ROOM, MarginRoom(margin, costs), RefusalReason.MARGIN_ROOM, margin_numbers, slot,
                 unchecked_note=MARGIN_NOT_CHECKED)  # fmt: skip


def margin_not_checked(result: LawResult) -> bool:
    """True for a margin-room refusal whose margin could not be read (reports show its note)."""
    return result.law == MARGIN_ROOM and result.note.startswith(MARGIN_NOT_CHECKED)
