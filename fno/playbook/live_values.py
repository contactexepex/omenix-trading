"""The day's live 15:00 feature values for one decision context (story D2), computed by B7's live features from the
research data the caller loads (the A4 snapshot, the panel up to the previous session, the events). Once the common
market pack exists (E2), the same features read the pack's inputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from ..research_engine.features import DecisionContext, Feature, FeatureValue, ResearchData
from .evaluate import LiveFeatureValues


class ComputedLiveFeatures(LiveFeatureValues):
    def __init__(self, features: Sequence[Feature], data: ResearchData):
        self.features, self.data = tuple(features), data

    def values(self, day: date, context: DecisionContext) -> Mapping[str, FeatureValue]:
        return {feature.name: feature.value(self.data, day, context) for feature in self.features}
