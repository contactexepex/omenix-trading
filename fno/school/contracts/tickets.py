"""The three counts (327 item 1): eligible (rule fired, structure built), fillable (every law and the quote gate
passed) and executed (filled in the account), per road, driver version and session."""

from dataclasses import dataclass
from datetime import date

from ..constants import RoadCode


@dataclass(frozen=True)
class OpportunityCounts:
    session: date
    road: RoadCode
    driver_id: str
    eligible: int
    fillable: int
    executed: int

    def __post_init__(self):
        if not self.eligible >= self.fillable >= self.executed >= 0:
            raise ValueError("counts must satisfy eligible >= fillable >= executed >= 0")
