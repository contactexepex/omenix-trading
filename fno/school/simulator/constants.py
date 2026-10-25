"""Fixed words and numbers of the simulator (story MS-SIM, 7.1-7.2). Practice only: nothing here licenses or counts."""

from datetime import date
from enum import StrEnum

PRACTICE_LABEL = "practice (simulator)"  # on every output and every record the simulator makes
SLOT_LABEL = "practice at the close; the pilot trades 15:00"
SIZE_GATE_NOT_TESTED_LABEL = "size gate not tested in practice"
SPREAD_LABEL = "spread learned from forward captures since 13 Oct 2026, measured at 15:00"
INSUFFICIENT_SPREAD_LINE = "insufficient spread data"

TICK = 0.05  # NSE's option tick
MIN_QUOTED_SESSIONS = 30  # a spread bucket below this reads "insufficient spread data" (response 327, correction 6)
DATA_END = date(2026, 10, 12)  # the day before the first forward capture of an index monthly (13 Oct 2026)


class PracticeRefusal(StrEnum):
    NOT_IN_DATA_SPEND = (
        "not_in_data_spend"  # the data is fresh or unregistered: an R1 card and a DATA_SPEND row come first
    )
    AI_DRIVER_NOT_SIMULATED = "ai_driver_not_simulated"  # the model has seen 2019-26
    INSUFFICIENT_SPREAD_DATA = "insufficient_spread_data"
