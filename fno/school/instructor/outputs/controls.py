"""REF's and RC1's results on a path's own road-slot (story MS-INS, part e; 327 correction 2): the net of each
control's entry decided on the same road and session, once it has closed; None while it abstained, was refused or is
still open, so the modifier reads "not testable" rather than guessing."""

from collections.abc import Iterable

from ....models import IST
from ...constants import RoadCode
from ..causes.evidence import Controls
from ..contracts import HeldPath

REF_CODE, RC1_CODE = "REF", "RC1"


def control_nets(paths: Iterable[HeldPath]) -> dict[tuple[str, RoadCode, object], float]:
    """(control code, road, entry session) -> net, from every closed path of REF and RC1."""
    nets = {}
    for path in paths:
        code = path.outcome.driver_id.split("@")[0]
        if code in (REF_CODE, RC1_CODE):
            nets[(code, path.outcome.road, _entry_day(path))] = path.outcome.net
    return nets


def controls_for(path: HeldPath, nets: dict) -> Controls:
    road, day = path.outcome.road, _entry_day(path)
    return Controls(nets.get((REF_CODE, road, day)), nets.get((RC1_CODE, road, day)))


def _entry_day(path: HeldPath):
    return path.outcome.entry.filled_at.astimezone(IST).date()
