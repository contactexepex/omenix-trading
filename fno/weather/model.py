"""`WeatherModel` (story M1, strategy): a weather forecaster's V6a (horizon 1) and V6b (horizon 5) probabilities for
day `d`, point in time at `d`'s 15:00 cutoff. Two implementations: `VixScaledWeather` (the model) and
`ColourBaseRate` (weather baseline v0)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..forecast_v4_rules.baselines import Value


class WeatherModel(ABC):
    @abstractmethod
    def forecast(self, d: date, horizon: int) -> Value:
        """The probability of a 2% log move in the next `horizon` regular sessions; missing or not eligible says so."""
