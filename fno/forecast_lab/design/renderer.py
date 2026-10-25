"""The signed-off design as the `PageRenderer` the composition root wires: one edition per `PageView`, chosen by
its `edition` ("morning" or "evening"). The picture and the attached file are the same one page: the owner asked
for one single page per edition (DESK_DECISIONS f9737bce, 11ef1b23)."""

from __future__ import annotations

from ..page.model import PageView
from ..page.render import PageRenderer
from .evening import render_evening
from .morning import render_morning
from .values import edition_of

MORNING = "morning"


class DesignRenderer(PageRenderer):
    def picture(self, view: PageView) -> str:
        return render_morning(view) if edition_of(view) == MORNING else render_evening(view)

    def details(self, view: PageView) -> str:
        return self.picture(view)
