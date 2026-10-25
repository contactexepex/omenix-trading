"""Policies as data (story B3, experiment 1 protocol section 6): ordered rules of a condition and a structure code;
the first rule whose condition holds gives the action, no rule means no trade. A condition with a `None` input never
holds (protocol section 5: "a condition with a None input counts as not met")."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass

from .features import FeatureValue

FeatureValues = Mapping[str, FeatureValue]  # feature name -> its value on the decision day


class Condition(ABC):
    @abstractmethod
    def holds(self, values: FeatureValues) -> bool: ...


@dataclass(frozen=True)
class Always(Condition):
    def holds(self, values: FeatureValues) -> bool:
        return True


@dataclass(frozen=True)
class Positive(Condition):
    """The feature is known and above zero."""

    feature: str

    def holds(self, values: FeatureValues) -> bool:
        value = values[self.feature]
        return value is not None and value > 0


@dataclass(frozen=True)
class NotPositive(Condition):
    """The feature is known and at most zero."""

    feature: str

    def holds(self, values: FeatureValues) -> bool:
        value = values[self.feature]
        return value is not None and value <= 0


@dataclass(frozen=True)
class Known(Condition):
    feature: str

    def holds(self, values: FeatureValues) -> bool:
        return values[self.feature] is not None


@dataclass(frozen=True)
class IsTrue(Condition):
    feature: str

    def holds(self, values: FeatureValues) -> bool:
        return values[self.feature] is True


@dataclass(frozen=True)
class IsFalse(Condition):
    """The feature is known and false (`None` is not false)."""

    feature: str

    def holds(self, values: FeatureValues) -> bool:
        return values[self.feature] is False


@dataclass(frozen=True)
class AllOf(Condition):
    parts: tuple[Condition, ...]

    def holds(self, values: FeatureValues) -> bool:
        return all(part.holds(values) for part in self.parts)


@dataclass(frozen=True)
class AnyOf(Condition):
    parts: tuple[Condition, ...]

    def holds(self, values: FeatureValues) -> bool:
        return any(part.holds(values) for part in self.parts)


@dataclass(frozen=True)
class Rule:
    condition: Condition
    action: str  # a structure code (SF, SC, BF)


class Policy(ABC):
    code: str

    @abstractmethod
    def decide(self, values: FeatureValues) -> str | None:
        """The structure code to trade, or None for no trade."""


@dataclass(frozen=True)
class RulePolicy(Policy):
    code: str
    rules: tuple[Rule, ...]

    def decide(self, values: FeatureValues) -> str | None:
        return next((rule.action for rule in self.rules if rule.condition.holds(values)), None)
