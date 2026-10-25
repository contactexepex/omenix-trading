"""G1, the cost wall (FACTORY_RULES section 2): expected net per trade on the conservative bound, after the round-trip
cost and the tail loss the gross does not already contain, must be above zero. The 2x ratio is a warning only."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import THIN_MARGIN_RATIO, GrossKind, Outcome
from .gross import GrossSource
from .round_trip import RoundTripCost

NO_STATED_EDGE = "no stated edge"
ASSUMED_HURDLE = "assumed hurdle: a cost-hurdle study, never a G1 pass for any idea"


@dataclass(frozen=True)
class Tail:
    """The maximum loss's probability and size; the screen uses the worse of the card's and a measured family rate."""

    probability: float
    loss: float  # rupees per trade
    in_gross: bool  # the gross figure already contains the card's tail (a measured history does)
    family_probability: float | None  # a measured rate of the structure's family, if one exists
    family_source: str | None

    def extra_loss(self) -> float:
        """Expected loss per trade beyond what the gross figure already contains."""
        worse = max(self.probability, self.family_probability or 0.0)
        contained = self.probability if self.in_gross else 0.0
        return (worse - contained) * self.loss


@dataclass(frozen=True)
class ScreenInputs:
    gross: GrossSource
    cost: RoundTripCost | None  # not needed when the card states no edge
    tail: Tail | None


@dataclass(frozen=True)
class Screen:
    outcome: Outcome
    reasons: tuple[str, ...]
    figures: dict[str, float]

    @property
    def thin_margin(self) -> bool:
        return "ratio" in self.figures and self.figures["ratio"] < THIN_MARGIN_RATIO


def screen(inputs: ScreenInputs) -> Screen:
    edge = inputs.gross.edge()
    if edge is None:
        hurdle = (ASSUMED_HURDLE,) if inputs.gross.kind == GrossKind.ASSUMED_HURDLE else ()
        return Screen(Outcome.SCREENED_OUT, (NO_STATED_EDGE, *hurdle), {})
    cost, tail = inputs.cost.rupees(), inputs.tail.extra_loss()
    net = edge.bound - cost - tail
    figures = {"bound": edge.bound, "expected": edge.expected, "cost": cost, "tail": tail, "net": net,
               "ratio": edge.expected / cost}  # fmt: skip
    outcome = Outcome.PASSED if net > 0 else Outcome.SCREENED_OUT
    return Screen(outcome, () if net > 0 else ("expected net at or below zero on the conservative bound",), figures)
