"""The replay root (story MS-P1j): a recorded session again, every write under the given folder: a local dashcam, local
accounts and ticket ledger, counts written but never committed, and a fixed clock. The captures, NSE's archived files
and the margin file are still read from where they are stored (read-only). It imports none of the pilot's real
stores (the Drive dashcam, the account sync, the committer), so a replay cannot write a pilot record by construction
(judge 512; `tests/school/fleet/test_wiring.py` checks the imports and the stores)."""

from datetime import date, datetime, time
from pathlib import Path

from ..config import ROOT
from ..models import IST
from .contracts.clock import FixedClock
from .fleet.replay_store import ReplayDashcam
from .fleet.runner import SchoolFleet
from .fleet_wiring import FleetStores, fleet_on

REPLAY_FILL_TIME = time(15, 20)  # after every road's capture window, as the run would be


def replay_clock(session: date) -> FixedClock:
    return FixedClock(datetime.combine(session, REPLAY_FILL_TIME, tzinfo=IST))


def build_replay_fleet(cfg: dict, session: date, folder: Path, root: Path = ROOT) -> SchoolFleet:
    folder, clock = Path(folder), replay_clock(session)
    stores = FleetStores(folder, ReplayDashcam(folder / "dashcam", clock), None, None, clock)
    return fleet_on(cfg, stores, root)
