"""Composition root of the report editions' content (stories FL1-1c and FL1-1d): the page builder over FL1's G13b
adapter, G13b's history and official closes, the evening's own close (A4h's record), the reasons' facts
(the repository's tables and P8's FII/DII flows archive), the renderer (the interim drawing until the designer's is
signed off) and headless Chromium for the picture."""

from __future__ import annotations

import functools
from datetime import date, time

from ..config import ROOT
from ..constants import NIFTY_SYMBOL
from ..recommend.report_guard import with_recommend_section
from ..research_data.calendar import SessionCalendar
from ..school.report_entry import school_report_inputs
from ..school.reports.guard import with_school_sections
from .a4h_closes import A4hTodayCloses
from .design.renderer import DesignRenderer
from .g13b_history import G13bHistory
from .maker import ReportMaker
from .page.builder import PageBuilder
from .page.camera import ChromiumCamera
from .page.cues import Section
from .page.facts import RepositoryFacts
from .ranges import Outcomes, RangeSource
from .sections.gift import GiftSection
from .sections.global_cues import SPECS, GlobalCueSection
from .sections.india import FlagsSection, VixSection
from .sections.levels import Levels
from .sessions import RegularSessions

PICTURE_WIDTH = 1100  # CSS pixels: the owner's signed-off design (DESK_DECISIONS 11ef1b23), drawn at 2x


def flows_reader(calendar: SessionCalendar):
    """Session -> (FII net, DII net) in Rs crore, up to a day, from P8's archive (read-only)."""
    from ..market_read_models.frame_inputs import FlowsReader
    from ..market_read_models.wiring import build_versioned_reader

    reader = FlowsReader(build_versioned_reader(), calendar)

    def flows(day: date) -> dict[date, tuple[float, float]]:
        return {c.day: (c.fii.net, c.dii.net) for c in reader.on(day).cash}

    return flows


PARTICIPANT_OI = "participant-oi"
EVENING_RUN = time(20, 5)  # the evening edition's time (owner, DESK_DECISIONS line 287): what A17 had by then


def build_sections(facts: RepositoryFacts, sessions: RegularSessions, official: Outcomes) -> tuple[Section, ...]:
    """The cues' Sections, one source each: A17's overnight cues (read only), India VIX from NSE's archived file, the
    day's flags, and GIFT Nifty (A22b's early file). A new source is one class and one line here."""
    from ..global_cues.as_of import OPEN
    from ..global_cues.wiring import build_reader
    from ..storage.data_wiring import build_drive_cache
    from ..storage.wiring import build_stored_index_close_files

    reader, known = functools.cache(build_reader), functools.cache(facts.facts)
    return (
        *(GlobalCueSection(reader, spec, {"morning": (OPEN,), "evening": (EVENING_RUN, OPEN)}) for spec in SPECS),
        VixSection(build_stored_index_close_files(), sessions.previous, lambda day: known(day).vix),
        FlagsSection(known),
        GiftSection(build_drive_cache(), lambda day: official.close(NIFTY_SYMBOL, sessions.previous(day))),
    )


def build_levels(calendar: SessionCalendar, sessions: RegularSessions) -> Levels:
    """The evening's levels and flows: NSE's F&O files and A8's participant OI through the raw-file libraries (stores
    first, then NSE), P8's flows archive; all read-only here (the evening routine archives them first)."""
    from ..storage.raw_source import ParticipantOiSource
    from ..storage.wiring import build_nifty_panel_files, build_participant_oi_library, daily_files

    fo_files, _ = build_nifty_panel_files()
    participant = daily_files(PARTICIPANT_OI, ParticipantOiSource, build_participant_oi_library())
    return Levels(fo_files, participant, flows_reader(calendar), sessions.previous)


def build_report_maker(ranges: RangeSource, forecasts, scores, calendar: SessionCalendar,
                       official: Outcomes) -> ReportMaker:  # fmt: skip
    """`forecasts`, `scores`: G13b's `RangeForecasts` and `RangeScores` over the synced Drive cache."""
    from ..storage.data_wiring import build_drive_cache

    facts, sessions = RepositoryFacts(ROOT, flows_reader(calendar)), RegularSessions(calendar)
    today, sections = A4hTodayCloses(build_drive_cache()), build_sections(facts, sessions, official)
    pages = PageBuilder(ranges, G13bHistory(forecasts, scores), facts, sessions, official=official, today_closes=today,
                        sections=sections, levels=build_levels(calendar, sessions))  # fmt: skip
    school = with_school_sections(ReportMaker(pages, DesignRenderer(), ChromiumCamera(width=PICTURE_WIDTH)),
                                  inputs=school_report_inputs)  # fmt: skip
    return with_recommend_section(school)  # REC1d: its own switch, outside the school's
