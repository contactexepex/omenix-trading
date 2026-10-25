"""Order time T from a delivery record, never from a clock (story E8 rules 1 and 12).

An entry's T is when the card that carries it reached the owner: Slack's own server time of the day's card, read from
T1's committed delivery record (the first attempt Slack accepted; a test post is not the card). A day without one has
no T, and its entries are "missed, card not delivered"."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from ...cards.deliveries import DeliveryLog


class CardTimes(ABC):
    @abstractmethod
    def delivered(self, day: date) -> datetime | None:
        """When that session's card reached the owner (time zone aware); None when it was never delivered."""


class DeliveredCards(CardTimes):
    def __init__(self, log: DeliveryLog):
        self.log = log

    def delivered(self, day: date) -> datetime | None:
        for _, metadata in self.log.attempts(day):
            slack = metadata.get("slack") or {}
            if not metadata.get("test") and slack.get("sent") and slack.get("server_time_utc"):
                return datetime.fromisoformat(slack["server_time_utc"])
        return None
