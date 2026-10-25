"""The gross edge per trade (FACTORY_RULES section 2, input 1): one strategy per source kind, each giving its
conservative bound and its expected figure, or no edge at all."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .constants import BOUND_LEVEL, GrossKind
from .t_bound import lower_bound


@dataclass(frozen=True)
class GrossEdge:
    bound: float  # the conservative bound the screen uses
    expected: float  # the expected gross, for the 2x warning only


class GrossSource(Protocol):
    kind: GrossKind
    source: str

    def edge(self) -> GrossEdge | None:
        """None when the card states no edge ("no stated edge")."""


@dataclass(frozen=True)
class MeasuredGross:
    mean: float
    sd: float
    n: int
    source: str
    kind: GrossKind = GrossKind.MEASURED

    def edge(self) -> GrossEdge:
        return GrossEdge(lower_bound(self.mean, self.sd, self.n, BOUND_LEVEL), self.mean)


@dataclass(frozen=True)
class StatedGross:
    """A published range's least favourable value, or arithmetic's least favourable input: bound and expected alike."""

    kind: GrossKind
    least_favourable: float
    source: str

    def edge(self) -> GrossEdge:
        return GrossEdge(self.least_favourable, self.least_favourable)


@dataclass(frozen=True)
class NoStatedEdge:
    """No source, or a cost-hurdle study's assumed hurdle (judge 97): the idea itself cannot pass G1."""

    kind: GrossKind
    source: str

    def edge(self) -> None:
        return None
