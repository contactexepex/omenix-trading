"""The forecast record (story G1; PROTOCOL.md section 6): one probability, or a recorded "no forecast", per forecaster,
forecast day and question.

Columns `book, date, cutoff, question, probability, method_or_version, pack_sha256`. `book` is one of the three books
or one of the three baselines; `cutoff` is the time the inputs were frozen, with its time zone, on the forecast day in
IST; `probability` is in [0, 1], or empty for "no forecast" (missing is never imputed); `pack_sha256` is the SHA-256 of
the input pack the forecast read (the market pack, story E2, live; the panel files for history).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime

from ..constants import FORECAST_QUESTIONS, FORECASTERS
from ..models import IST

RECORD_COLUMNS = ("book", "date", "cutoff", "question", "probability", "method_or_version", "pack_sha256")
SHA256 = re.compile(r"[0-9a-f]{64}")


class ForecastRecordError(ValueError):
    """A forecast record that breaks the protocol's schema."""


def _text(name: str, value: str) -> str:
    if not value or value != value.strip() or any(ch in value for ch in ",\r\n\x00"):
        raise ForecastRecordError(f"{name} must be non-empty single-line text without commas: {value!r}")
    return value


@dataclass(frozen=True)
class ForecastRecord:
    book: str
    date: date
    cutoff: datetime
    question: str
    probability: float | None  # None: "no forecast" recorded
    method_or_version: str
    pack_sha256: str

    def __post_init__(self):
        if self.book not in FORECASTERS:
            raise ForecastRecordError(f"book must be one of {FORECASTERS}, not {self.book!r}")
        if self.question not in FORECAST_QUESTIONS:
            raise ForecastRecordError(f"question must be one of {FORECAST_QUESTIONS}, not {self.question!r}")
        if self.cutoff.tzinfo is None or self.cutoff.astimezone(IST).date() != self.date:
            raise ForecastRecordError(f"cutoff {self.cutoff} must carry its time zone and fall on {self.date} (IST)")
        p = self.probability
        if p is not None and (isinstance(p, bool) or not math.isfinite(p) or not 0 <= p <= 1):
            raise ForecastRecordError(f"probability must be in [0, 1] or empty (no forecast), not {p!r}")
        _text("method_or_version", self.method_or_version)
        if not SHA256.fullmatch(self.pack_sha256):
            raise ForecastRecordError(f"pack_sha256 must be 64 lowercase hex characters, not {self.pack_sha256!r}")

    def row(self) -> dict[str, str]:
        return {
            "book": self.book,
            "date": self.date.isoformat(),
            "cutoff": self.cutoff.isoformat(),
            "question": self.question,
            "probability": "" if self.probability is None else repr(float(self.probability)),
            "method_or_version": self.method_or_version,
            "pack_sha256": self.pack_sha256,
        }

    @classmethod
    def from_row(cls, row: dict[str, str]) -> ForecastRecord:
        if tuple(row) != RECORD_COLUMNS:
            raise ForecastRecordError(f"columns must be {RECORD_COLUMNS}")
        try:
            probability = float(row["probability"]) if row["probability"] != "" else None
            day, cutoff = date.fromisoformat(row["date"]), datetime.fromisoformat(row["cutoff"])
        except ValueError as error:
            raise ForecastRecordError(f"unreadable record {row}: {error}") from error
        return cls(row["book"], day, cutoff, row["question"], probability, row["method_or_version"],
                   row["pack_sha256"])  # fmt: skip
