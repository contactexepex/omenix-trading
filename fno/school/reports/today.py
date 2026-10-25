"""The 08:50 "Today" section (story MS-P1g): which roads are open and why one is closed, the planned paper trades with
their worst loss, the banner. Controls and measurement-only drivers are never shown as candidates (story 3.2)."""

from datetime import date

from ..constants import DriverRole
from ..contracts.reports import SectionText
from .banner import banner_for, banner_line
from .inputs import TodayInputs
from .lines import RUPEE, footer, paper_title, road_status_line

TITLE = "Today"
NO_CANDIDATE = "No candidate today: nothing is planned."
NOT_PLANNED = "Not planned, the driver failed: {drivers}"  # MS-P1j4: a failed driver is named, never silent
NO_PLAN = "No plan can be made today: no road is open."  # MS-P1j4: no data to plan from is not "nothing proposed"
PLAN_NOTE = "Each planned trade is booked at its road's 15:00 slot at today's quotes, or dropped."
# Every line names its source (orchestrator, 22 Oct 2026): today's captures do not exist at 08:50
SOURCE = "plan from {day:%d %b %Y} 15:00 data, indicative prices, not today's quotes"


class TodaySection:
    def __init__(self, inputs: TodayInputs):
        self.inputs = inputs

    def render(self, session: date) -> SectionText:
        days = self.inputs.roads(session)
        shown = [t for t in self.inputs.plan(session) if t.role is DriverRole.RULE]
        closed = sum(not d.status.open for d in days)
        banner = banner_for(closed, len(shown))
        source = SOURCE.format(day=self.inputs.source(session))
        plan = [f"{t.driver_id} {t.road}: {t.structure}, worst loss {RUPEE.format(amount=t.worst_loss)}" for t in shown]
        body = (PLAN_NOTE, *plan) if plan else (NO_CANDIDATE if any(d.status.open for d in days) else NO_PLAN,)
        failed = self.inputs.not_planned(session)
        problems = (NOT_PLANNED.format(drivers="; ".join(failed)),) if failed else ()
        labelled = (banner_line(banner), road_status_line(days), *body, *problems)
        lines = tuple(f"{line} ({source})" for line in labelled)
        return SectionText(paper_title(TITLE), (*lines, *footer()), banner)
