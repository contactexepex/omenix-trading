"""The card itself and its builder (story T1). `CardBuilder` asks each source for its section; a source that fails
becomes a named missing item, so the card always arrives (criterion 10). The card never computes a number of its own."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date

from ..constants import CARD_DATA_CHECK_FAILED, CARD_VALID_UNTIL, CardStatus
from .sections import (
    WEATHER_BLOCKS,
    CardSection,
    CardWarning,
    ForecastSource,
    StatusSource,
    UsedRecord,
    WarningSource,
    WeatherSource,
)
from .session import SessionAnswer

UNAVAILABLE = "{title}: not available on this card"
FAILED = "{title} source failed ({error})"
OWNER_UNAVAILABLE = (
    "If you cannot act by {until:%H:%M} IST, the paper record assumes: no action (nothing is opened or closed). "
    "Owner availability calendar (E8) not built yet."
)


@dataclass(frozen=True)
class TradeCard:
    day: date
    session: str  # e.g. "NSE regular session", or that the calendar could not say
    status: CardStatus
    reason_code: str
    sections: tuple[CardSection, ...]  # status first, then weather and forecasts
    previous_misses: tuple[str, ...]
    context: CardSection = CardSection("session", ())  # records used and gaps that are not a shown section
    warning: CardWarning | None = None  # story T1e: a failed or refused step today; the renderer places it

    @property
    def _all(self) -> tuple[CardSection, ...]:
        return (self.context, *self.sections)

    @property
    def used(self) -> tuple[UsedRecord, ...]:
        seen = {}
        for section in self._all:
            for record in section.used:
                seen.setdefault(record.path, record)
        return tuple(seen.values())

    @property
    def missing(self) -> tuple[str, ...]:
        return tuple(item for section in self._all for item in section.missing)

    @property
    def owner_unavailable(self) -> str:
        return OWNER_UNAVAILABLE.format(until=CARD_VALID_UNTIL)


STATUS_FAILED = (f"Status: {CardStatus.NO_TRADE} ({CARD_DATA_CHECK_FAILED})", "Reason: the status could not be read")


def _failed(title: str, error: Exception, lines: tuple[str, ...] | None = None) -> CardSection:
    missing = FAILED.format(title=title, error=type(error).__name__)  # by type only: the message stays off the record
    return CardSection(title, lines or (UNAVAILABLE.format(title=title),), missing=(missing,))


def _guarded(title: str, make: Callable[[], CardSection], extra: tuple[str, ...] = ()) -> CardSection:
    try:
        return make()
    except Exception as error:  # noqa: BLE001 - any failure is named on the card, never a lost card
        return _failed(title, error, (UNAVAILABLE.format(title=title), *extra) if extra else None)


class CardBuilder:
    """`warnings` (story T1e) is asked on its own, so a status source that fails never hides a failed step."""

    def __init__(self, status: StatusSource, weather: WeatherSource, forecasts: ForecastSource,
                 warnings: WarningSource | None = None):  # fmt: skip
        self.status_source, self.weather_source, self.forecast_source = status, weather, forecasts
        self.warning_source = warnings

    def build(self, day: date, session: SessionAnswer, previous_misses: tuple[str, ...] = ()) -> TradeCard:
        status, code = self._status(day)
        warning, context = self._warning(day, session.context)
        weather = _guarded(
            "weather", lambda: self.weather_source.weather(day), (WEATHER_BLOCKS,)
        )  # a crash still blocks
        forecasts = _guarded("forecasts", lambda: self.forecast_source.forecasts(day))
        # v1 has no trade fields (slice B), so its status is NO TRADE whatever a source says: it never shows a trade
        sections = (status, weather, forecasts)
        return TradeCard(day, session.note, CardStatus.NO_TRADE, code, sections, previous_misses, context, warning)

    def _status(self, day: date) -> tuple[CardSection, str]:
        try:
            reading = self.status_source.status(day)
        except Exception as error:  # noqa: BLE001 - the card still goes out as NO TRADE, naming the failure
            return _failed("status", error, STATUS_FAILED), CARD_DATA_CHECK_FAILED
        return reading.section, reading.reason_code

    def _warning(self, day: date, context: CardSection) -> tuple[CardWarning | None, CardSection]:
        if self.warning_source is None:
            return None, context
        try:
            return self.warning_source.warning(day), context
        except Exception as error:  # noqa: BLE001 - named as missing, never a lost card
            return None, replace(
                context, missing=(*context.missing, FAILED.format(title="warning", error=type(error).__name__))
            )
