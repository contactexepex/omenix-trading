"""The practice fleet (story MS-SIM-d2; orchestrator, 22 Oct: a second instance of MS-P1j's own `SchoolFleet`, wired
here with practice dependencies, never a second runner). Wiring only: each choice below is one object handed in.

One fleet is built per session and scenario, because the session's charges (dated STT) and the pilot's drivers, priced
on those charges, are fixed when they are built. The accounts persist across sessions under `home`, one folder per
scenario, never under the pilot's `journal/school`."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ....nse_margins.road_wiring import build_road_margin
from ....research_data.calendar import SessionCalendar
from ....risk.margins import StressedMargin
from ...contracts.roads import ROADS, Road
from ...drivers.wiring import build_school_drivers
from ...execution.practice_wiring import PRACTICE, build_practice_fill_port
from ...fleet.counts_file import SessionCounts
from ...fleet.entry_mids import DashcamEntryMids
from ...fleet.runner import SchoolFleet
from ...fleet_wiring import FleetStores, books_on
from ...safety.practice_wiring import build_practice_safety_laws
from ...settings import school_settings
from ..history.ports import HistoricalChain
from ..source.catalogue import HistoricalRoadCatalogue
from ..source.snapshots import HistoricalRoadSource
from ..spreads.model import Scenario, SpreadModel
from ..terms import DatedTerms
from ..windows import PracticeWindows
from .clock import practice_clock
from .dashcam import DASHCAM_HOME, PracticeDashcam
from .dated import cfg_on
from .drivers import simulable
from .gate import PracticeQualityGate
from .margin import latest_factor
from .spots import ChainSpotHistory

MarginFor = Callable[[dict], StressedMargin]


@dataclass(frozen=True)
class PracticeParts:
    """What a practice run reads, built once: the archive's chain, the dated terms, the window, the learned spreads."""

    cfg: dict
    root: Path
    factor_file: Path
    calendar: SessionCalendar
    chain: HistoricalChain
    terms: DatedTerms
    windows: PracticeWindows
    spreads: SpreadModel


def practice_margin(parts: PracticeParts, cfg: dict) -> StressedMargin:
    """Law 3 is never skipped: that session's archived SPAN file x the latest stress factor (orchestrator, 23 Oct)."""
    return build_road_margin(cfg, factor=latest_factor(parts.factor_file))


class HomeUnderThePilot(ValueError):
    """A practice home inside the pilot's records: refused before anything is built or written."""


def _refuse_pilot_paths(home: Path, root: Path) -> None:
    for pilot in (root / "journal", root / "research" / "school", root / "receipts"):
        if Path(home).resolve().is_relative_to(pilot.resolve()):
            raise HomeUnderThePilot(f"{home} is under the pilot's {pilot.relative_to(root)}")


def build_practice_fleet(
    parts: PracticeParts, session: date, scenario: Scenario, home: Path,
    margin_for: MarginFor | None = None, roads: Sequence[Road] = ROADS,
) -> SchoolFleet:  # fmt: skip
    _refuse_pilot_paths(home, parts.root)
    cfg = cfg_on(parts.cfg, parts.terms, session)
    settings, clock = school_settings(cfg), practice_clock(session)
    dashcam = PracticeDashcam(Path(home) / DASHCAM_HOME, clock)
    books = books_on(
        cfg, FleetStores(Path(home), dashcam, None, None, clock), build_practice_fill_port(cfg), parts.root
    )
    margin = (margin_for or (lambda c: practice_margin(parts, c)))(cfg)
    return SchoolFleet(
        settings,
        HistoricalRoadCatalogue(parts.calendar, parts.chain, parts.terms, parts.windows, roads),
        HistoricalRoadSource(parts.chain, parts.spreads, scenario, parts.windows),
        PracticeQualityGate(),
        ChainSpotHistory(parts.chain, parts.calendar),
        simulable(build_school_drivers(cfg, parts.root)),
        lambda marks: build_practice_safety_laws(cfg, settings, marks, margin),
        books, dashcam, SessionCounts(Path(home), None), lambda _session: None, DashcamEntryMids(dashcam), clock,
        rules=PRACTICE,
    )  # fmt: skip
