"""One session's weather (story M1): both forecasters' V6a and V6b probabilities, G7's base rates, the operative
colour (the model's, decision 71, labelled "not yet proven"; v0's beside it), the drivers, and the rows for G7's v4
record files. Every input is first seen before the day's 15:00 cutoff: closes and VIX up to the previous regular
session, events announced by the day."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

from ..constants import V6_BIG_MOVE_1S, V6_BIG_MOVE_5S
from ..forecast_v4_rules.baselines import BaseRate, Value, before
from ..forecast_v4_rules.records import BASELINE, RULE, SLOT_REPORTED, SLOT_RULES, Record, record
from ..forecast_v4_rules.series import DayValue, big_move_outcomes
from .checklist_v0 import Event, Row
from .colour import weather_colour
from .constants import (
    WEATHER_BASELINE_V0,
    WEATHER_MODEL_VIX,
    WEATHER_OPERATIVE_MODEL,
    WEATHER_OPERATIVE_PROVEN,
    WeatherColour,
)
from .drivers import public_drivers
from .model import WeatherModel
from .v0_live import ChecklistV0, ColourBaseRate, Horizon
from .vix_scaled import VixScaledWeather

QUESTIONS = ((V6_BIG_MOVE_1S, 1), (V6_BIG_MOVE_5S, 5))
FORECASTERS = {WEATHER_MODEL_VIX: (RULE, SLOT_RULES), WEATHER_BASELINE_V0: (BASELINE, SLOT_REPORTED)}
NOT_YET_PROVEN = "not yet proven: G8 has not scored it against v0 and the base rate"
SCORED = "scored"
PROVEN = "proven by G8 against v0 and the base rate"


@dataclass(frozen=True)
class WeatherInputs:
    rows: list[Row]  # regular sessions: day, NIFTY close, India VIX close
    closes_lines: list[str]  # the same rows as committed text (for the inputs' hash)
    events: list[Event]
    horizon: Horizon
    method_sha256: str


@dataclass(frozen=True)
class DayWeather:
    public: dict
    rows: dict[tuple[str, str], Record]  # (forecaster, question) -> G7's v4 row


class WeatherDays:
    def __init__(self, inputs: WeatherInputs):
        self.inputs = inputs
        self.days = [r.day for r in inputs.rows]
        closes = [DayValue(r.day, r.close) for r in inputs.rows]
        self.v0 = ChecklistV0(inputs.rows, inputs.events, inputs.horizon)
        outcomes = {h: big_move_outcomes(closes, h) for _, h in QUESTIONS}
        self.base = {q: BaseRate(outcomes[h]) for q, h in QUESTIONS}
        self.models: dict[str, WeatherModel] = {
            WEATHER_MODEL_VIX: VixScaledWeather(inputs.rows), WEATHER_BASELINE_V0: ColourBaseRate(self.v0, outcomes),
        }  # fmt: skip
        self._prefix = _prefix_hashes(inputs.closes_lines)

    def values(self, d: date) -> dict[str, dict[str, Value]]:
        found = {name: {q: model.forecast(d, h) for q, h in QUESTIONS} for name, model in self.models.items()}
        return found | {"base_rate": {q: self.base[q].forecast(d) for q, _ in QUESTIONS}}

    def colours(self, d: date, values: dict | None = None) -> tuple[WeatherColour, WeatherColour, WeatherColour]:
        """(operative, the model's, v0's): the operative one is the model's unless decision 71 is reversed."""
        values = values or self.values(d)
        model, base = values[WEATHER_MODEL_VIX], values["base_rate"]
        model_colour = weather_colour(*(model[q].value for q, _ in QUESTIONS), *(base[q].value for q, _ in QUESTIONS))
        v0_colour = self.v0.colour(d) or WeatherColour.NOT_SCORED
        return (model_colour if WEATHER_OPERATIVE_MODEL == WEATHER_MODEL_VIX else v0_colour), model_colour, v0_colour

    def day(self, d: date, label: str, made_at: str, red: dict) -> DayWeather:
        values = self.values(d)
        colour, model_colour, v0_colour = self.colours(d, values)
        audit = dict(label=label, method_sha256=self.inputs.method_sha256, inputs_sha256=self._inputs_sha(d),
                     made_at=made_at)  # fmt: skip
        public = {
            "day": d.isoformat(), "label": label, "colour": str(colour), "operative": WEATHER_OPERATIVE_MODEL,
            "proof": PROVEN if WEATHER_OPERATIVE_PROVEN else NOT_YET_PROVEN,
            "status": _status(values[WEATHER_OPERATIVE_MODEL], values["base_rate"]),
            "model_colour": str(model_colour), "v0_colour": str(v0_colour), "v0_status": self._v0_status(d),
            "probabilities": {name: _shown(v) for name, v in values.items()}, **red,
            "drivers": public_drivers(self.v0.inputs(d), self.v0.events_ahead(d)), **audit,
        }  # fmt: skip
        rows = {
            (f, q): record(d, q, values[f][q].status, values[f][q].value, kind=kind, slot=slot, **audit)
            for f, (kind, slot) in FORECASTERS.items()
            for q, _ in QUESTIONS
        }
        return DayWeather(public, rows)

    def _v0_status(self, d: date) -> str:
        """`scored`, or `not scored:` and why (owner, 16 Oct: every calendar user fails loudly, by name)."""
        reason = self.v0.unscored_reason(d)
        return f"{WeatherColour.NOT_SCORED}: {reason}" if reason else SCORED

    def latest_row(self, d: date) -> date | None:
        """The last committed session before `d` (live: it must be the previous regular session)."""
        i = before(self.days, d)
        return self.days[i - 1] if i else None

    def _inputs_sha(self, d: date) -> str:
        """SHA-256 of the closes rows before `d` and the events announced on or before `d`."""
        digest = hashlib.sha256(self._prefix[before(self.days, d)].encode())
        for e in self.inputs.events:
            if e.announced <= d:
                digest.update(f"{e.day},{e.kind},{e.announced}\n".encode())
        return digest.hexdigest()


def _status(operative: dict[str, Value], base: dict[str, Value]) -> str:
    """`scored`, or `not scored:` and each missing figure with its status (the entry gate reads why, owner "4 A")."""
    figures = {**{f"{q} p": v for q, v in operative.items()}, **{f"{q} base rate": v for q, v in base.items()}}
    missing = [f"{name} {v.status}" for name, v in figures.items() if v.value is None]
    return f"{WeatherColour.NOT_SCORED}: {', '.join(missing)}" if missing else SCORED


def _shown(values: dict[str, Value]) -> dict:
    return {q: {"status": v.status, "value": v.value} for q, v in values.items()}


def _prefix_hashes(lines: list[str]) -> list[str]:
    digest, out = hashlib.sha256(), [hashlib.sha256().hexdigest()]
    for line in lines:
        digest.update((line + "\n").encode())
        out.append(digest.hexdigest())
    return out
