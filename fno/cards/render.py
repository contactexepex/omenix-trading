"""How a card is shown (story T1): `CardRenderer` is the interface (Slack text today, the dashboard later: one class
each). The first line always says PAPER ONLY and what to do (design 6.5: "information, no action" on a NO TRADE day)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..constants import CARD_VALID_UNTIL
from .card import TradeCard
from .sections import CardWarning

FIRST_LINE = "PAPER ONLY. Omenix F&O daily card, {day:%a %d %b %Y} ({session}). Information, no action."
PREVIOUS = "Previous card: {miss}"
MISSING = "Missing: {items}"
VALID = "Valid until {until:%H:%M} IST."
ISSUANCE = (
    "Issuance time: this message's Slack server timestamp; GitHub's push receipt of its delivery record is the second "
    "witness. Committer time is never used."
)
RECORDS = "Records used (SHA-256 of the committed bytes):"
RECORD_LINE = "  {path} {sha256}"
NO_RECORDS = "  none"


class CardRenderer(ABC):
    @abstractmethod
    def render(self, card: TradeCard) -> str:
        """The card as one message."""


class SlackTextRenderer(CardRenderer):
    def render(self, card: TradeCard) -> str:
        status, *others = card.sections
        first = FIRST_LINE.format(day=card.day, session=card.session)
        lines = [*opening(first, card.warning), *status.lines, card.owner_unavailable]
        lines += [PREVIOUS.format(miss=miss) for miss in card.previous_misses]
        for section in others:
            lines += ["", *section.lines]
        lines += ["", MISSING.format(items="; ".join(card.missing) or "none"), VALID.format(until=CARD_VALID_UNTIL)]
        lines += [ISSUANCE, RECORDS]
        lines += [RECORD_LINE.format(path=r.path, sha256=r.sha256) for r in card.used] or [NO_RECORDS]
        return "\n".join(lines)


def opening(first: str, warning: CardWarning | None) -> list[str]:
    """Story T1e: where the warning goes, the one place to change if the owner picks the other placement. Today (a):
    its headline before T1's first line (PAPER ONLY stays on line 1, the warning is in a phone's preview), its detail
    on line 2. Option (b) would be `[first, f"{warning.headline} {warning.detail}"]`."""
    return [first] if warning is None else [f"{warning.headline} {first}", warning.detail]
