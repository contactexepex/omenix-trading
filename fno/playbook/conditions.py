"""A version's entry conditions on the day's live 15:00 feature values (story D2; B7's validated live versions, never
the close-only research features). A condition on an unknown value (None) is not met, as in the research."""

from __future__ import annotations

import operator
from collections.abc import Mapping

from ..constants import OPERATOR_ABOVE, OPERATOR_AT_LEAST, OPERATOR_AT_MOST, OPERATOR_BELOW, OPERATOR_IS
from ..research_engine.features import FeatureValue
from .schema import EntryCondition, Strategy
from .vocabulary import FEATURES

COMPARE = {
    OPERATOR_ABOVE: operator.gt, OPERATOR_AT_LEAST: operator.ge, OPERATOR_BELOW: operator.lt,
    OPERATOR_AT_MOST: operator.le, OPERATOR_IS: lambda value, flag: isinstance(value, bool) and value == flag,
}  # fmt: skip


def live_value(condition: EntryCondition, values: Mapping[str, FeatureValue]) -> FeatureValue:
    return values.get(FEATURES[condition.feature].live_version)


def unmet_conditions(strategy: Strategy, values: Mapping[str, FeatureValue]) -> list[str]:
    """Each condition that does not hold, written out with the live value it saw; empty when the rule fires."""
    unmet = []
    for condition in strategy.entry_conditions:
        value = live_value(condition, values)
        if value is None or not COMPARE[condition.operator](value, condition.threshold):
            live = FEATURES[condition.feature].live_version
            unmet.append(f"{live} {condition.operator} {condition.threshold} (live value {value})")
    return unmet
