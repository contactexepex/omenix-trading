"""Which drivers a practice run may use (story MS-SIM-d2, criterion 5): the rule, control and measurement-only drivers
of the pilot. An AI driver is never simulated: the model has seen 2019-26, so history is not out of sample for it."""

from collections.abc import Sequence

from ...contracts.decisions import Driver
from ..constants import PracticeRefusal

AI_ROLE = "ai"


class AiDriverNotSimulated(ValueError):
    """A card with the AI role or family was offered to a practice run."""

    def __init__(self, driver_id: str):
        super().__init__(f"{PracticeRefusal.AI_DRIVER_NOT_SIMULATED}: {driver_id}")
        self.reason = PracticeRefusal.AI_DRIVER_NOT_SIMULATED


def simulable(drivers: Sequence[Driver]) -> tuple[Driver, ...]:
    """The drivers unchanged, or `AiDriverNotSimulated` naming the first AI card (nothing is dropped silently)."""
    for driver in drivers:
        card = driver.card
        if str(getattr(card.role, "value", card.role)) == AI_ROLE or str(card.family) == AI_ROLE:
            raise AiDriverNotSimulated(card.driver_id)
    return tuple(drivers)
