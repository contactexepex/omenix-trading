"""How the page is drawn (stories FL1-1c and FL1-1d): a port. The owner's signed-off design (`design.renderer.
DesignRenderer`, owned by the designer's session) is the one implementation; the interim drawing was removed once it
went live (judge 454)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .model import PageView


class PageRenderer(ABC):
    @abstractmethod
    def picture(self, view: PageView) -> str:
        """The HTML the picture is drawn from: what a reader sees in the message."""

    @abstractmethod
    def details(self, view: PageView) -> str:
        """The attached HTML file: everything behind the picture."""
