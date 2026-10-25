"""Book 1's forecast method, version 1 (story G3; PROTOCOL.md section 5). Its SHA-256 is in every Book 1 record, so
a record names exactly the method that made it; any change to this file is a new version.

For each question, the mean of the question's two baselines (questions 1-2: risk-neutral and base rate; questions 3-5:
base rate and the statistical model). One available: that one. None: "no forecast" (never imputed). Book 1 never
refits on outcomes: the baselines' frozen windows and refit schedule are its only learning.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path

from ..constants import FORECAST_QUESTIONS
from .comparisons import baselines_for

BOOK1_VERSION = "book1/v1"

Probabilities = Mapping[str, float | None]


def method_sha256() -> str:
    """The SHA-256 of this file: the method's identity in every record."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def method_label() -> str:
    return f"{BOOK1_VERSION}/sha256:{method_sha256()}"


def book1_probabilities(by_baseline: Mapping[str, Probabilities]) -> dict[str, float | None]:
    """Book 1's five probabilities from each baseline's (missing baselines count as no forecast)."""
    out: dict[str, float | None] = {}
    for question in FORECAST_QUESTIONS:
        values = [by_baseline.get(b, {}).get(question) for b in baselines_for(question)]
        available = [v for v in values if v is not None]
        out[question] = sum(available) / len(available) if available else None
    return out
