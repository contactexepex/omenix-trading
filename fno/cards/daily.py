"""One day's card, before it is issued (story T1): the session calendar decides whether there is a card, the previous
session's delivery decides what the card must say went wrong, and the builder and renderer make it."""

from __future__ import annotations

from datetime import date

from .card import CardBuilder, TradeCard
from .deliveries import DeliveryLog, misses
from .render import CardRenderer
from .session import SessionCheck

NO_PREVIOUS = "the previous session could not be found in the calendar, so its card was not checked"
UNREADABLE = "the {day} card's delivery record could not be read ({error})"


class DailyCard:
    def __init__(self, sessions: SessionCheck, builder: CardBuilder, renderer: CardRenderer, deliveries: DeliveryLog):
        self.sessions, self.builder, self.renderer, self.deliveries = sessions, builder, renderer, deliveries

    def prepare(self, day: date) -> tuple[TradeCard, str] | None:
        """The card and its text, or None on a day that is not an NSE session."""
        answer = self.sessions.answer(day)
        if not answer.is_session:
            return None
        previous = self._previous_misses(answer.previous)
        card = self.builder.build(day, answer, previous)
        return card, self.renderer.render(card)

    def _previous_misses(self, previous: date | None) -> tuple[str, ...]:
        if previous is None:
            return (NO_PREVIOUS,)
        try:
            return misses(self.deliveries, previous)
        except Exception as error:  # noqa: BLE001 - a bad earlier record is named, never a lost card
            return (UNREADABLE.format(day=previous, error=type(error).__name__),)
