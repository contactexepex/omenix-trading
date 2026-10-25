"""The G1-G3 inputs of an idea card's block (story R1b), read only when their gate runs: a card lacking one is
refused by name, never given a default (judge 261)."""

from __future__ import annotations

from dataclasses import dataclass

from ..constants import SIDE_BUY, SIDE_SELL
from .card import IdeaCard
from .constants import GrossKind
from .cost_wall import ScreenInputs, Tail
from .fields import CardError, Fields
from .gross import GrossSource, MeasuredGross, NoStatedEdge, StatedGross
from .round_trip import Leg, LegsCost, RoundTripCost, StatedCost

_GROSS = {GrossKind.MEASURED: ("kind", "source", "mean", "sd", "n"),
          GrossKind.PUBLISHED: ("kind", "source", "least_favourable"),
          GrossKind.ARITHMETIC: ("kind", "source", "least_favourable"),
          GrossKind.NONE: ("kind", "source"), GrossKind.ASSUMED_HURDLE: ("kind", "source")}  # fmt: skip
_TAIL = ("probability", "loss", "in_gross", "family_probability", "family_source")
_LEG = ("instrument", "side", "units", "entry", "exit", "settlement", "pad", "pad_source")
_INDEX_OPTION, _STOCK_OPTION = "index_option", "stock_option"


@dataclass(frozen=True)
class PlanInputs:
    sd_per_trade: float
    frequency_per_year: float
    pass_level: float  # the registered one-sided pass level; z comes from it


def _block(card: IdeaCard) -> Fields:
    if card.inputs is None:
        raise CardError(f"{card.path}: the card was not read from its block")
    return card.inputs


def screen_inputs(card: IdeaCard, charges: dict) -> ScreenInputs:
    gross = _gross(_block(card).section("gross"))
    if gross.edge() is None:
        return ScreenInputs(gross, None, None)
    return ScreenInputs(gross, _cost(_block(card).section("cost"), charges), _tail(_block(card).section("tail")))


def spend_inputs(card: IdeaCard) -> tuple[list[str], str]:
    return _block(card).texts("data_sets"), _block(card).text("measures")


def plan_inputs(card: IdeaCard) -> PlanInputs:
    block = _block(card)
    sd, frequency, level = (
        block.positive("sd_per_trade"),
        block.positive("frequency_per_year"),
        block.number("pass_level"),
    )
    if not 0 < level < 0.5:
        raise block.refuse("pass_level", "must be a one-sided level between 0 and 0.5")
    return PlanInputs(sd, frequency, level)


@dataclass(frozen=True)
class RegistrationInputs:
    playbook_name: str
    playbook_version: int
    minimum_useful_net: float  # rupees a trade: the stop rule's "minimum useful net" (Test B)


def registration_inputs(card: IdeaCard) -> RegistrationInputs:
    block = _block(card)
    return RegistrationInputs(block.slug("playbook_name"), block.count("playbook_version"),
                              block.positive("minimum_useful_net"))  # fmt: skip


def _gross(fields: Fields) -> GrossSource:
    kind = GrossKind(fields.choice("kind", list(GrossKind)))
    fields.only(_GROSS[kind])
    source = fields.text("source")
    if kind == GrossKind.MEASURED:
        if fields.count("n") < 2:
            raise fields.refuse("n", "must be at least 2 trades for a bound")
        return MeasuredGross(fields.number("mean"), fields.positive("sd"), fields.count("n"), source)
    if kind in (GrossKind.PUBLISHED, GrossKind.ARITHMETIC):
        return StatedGross(kind, fields.number("least_favourable"), source)
    return NoStatedEdge(kind, source)


def _tail(fields: Fields) -> Tail:
    fields.only(_TAIL)
    family = fields.has("family_probability") or fields.has("family_source")
    return Tail(
        probability=fields.probability("probability"),
        loss=fields.not_negative("loss"),
        in_gross=fields.flag("in_gross"),
        family_probability=fields.probability("family_probability") if family else None,
        family_source=fields.text("family_source") if family else None,
    )


def _cost(fields: Fields, charges: dict) -> RoundTripCost:
    if fields.has("legs") == fields.has("measured"):
        raise fields.refuse("measured", "or 'legs' must be given, not both and not neither")
    if fields.has("measured"):
        fields.only(("measured", "source"))
        return StatedCost(fields.positive("measured"), fields.text("source"))
    fields.only(("legs",))
    return LegsCost(tuple(_leg(leg) for leg in fields.sections("legs")), charges)


def _leg(fields: Fields) -> Leg:
    fields.only(_LEG)
    if fields.has("exit") == fields.has("settlement"):
        raise fields.refuse("exit", "or 'settlement' must be given, not both and not neither")
    if fields.choice("instrument", (_INDEX_OPTION, _STOCK_OPTION)) == _STOCK_OPTION and fields.has("settlement"):
        # stock options settle physically, and C1 has no physical-settlement charge yet (judge 266)
        raise fields.refuse("settlement", "is cash settlement only: a stock-option card states a measured cost")
    return Leg(
        side=fields.choice("side", (SIDE_BUY, SIDE_SELL)),
        units=fields.count("units"),
        entry=fields.positive("entry"),
        exit=fields.not_negative("exit") if fields.has("exit") else None,
        settlement=fields.not_negative("settlement") if fields.has("settlement") else None,
        pad=fields.not_negative("pad"),
        pad_source=fields.text("pad_source"),
    )
