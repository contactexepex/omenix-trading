"""The promotion checks (docs/PIPELINE_DESIGN.md, "Promotion checks"): each looks at one staged copy and returns the
reason it must not become a record, or None. The gate runs all of them; a file is promoted only when none objects.
Idempotency (the record already holds the file) is the gate's own step, as it needs the record."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta

from fno.ingestion.promotion.staging import StagedCopy
from fno.ingestion.storage.coverage import Validator
from fno.shared.models import IST


@dataclass(frozen=True)
class Candidate:
    copy: StagedCopy
    day: date  # the session the file claims to be for
    filename: str


class PromotionCheck(ABC):
    name: str = "check"

    @abstractmethod
    def problem(self, candidate: Candidate) -> str | None:
        """Why this copy must not be promoted; None when this check is satisfied."""


class SchemaCheck(PromotionCheck):
    """The dataset's own content check (the one the librarian and the coverage check use): parses into the expected
    columns and types, not truncated, for the day its name claims."""

    name = "schema"

    def __init__(self, validate: Validator):
        self.validate = validate

    def problem(self, candidate: Candidate) -> str | None:
        try:
            self.validate(candidate.filename, candidate.copy.data)
        except ValueError as exc:
            return str(exc)
        return None


class FreshnessCheck(PromotionCheck):
    """A file cannot be for a session after the day it was fetched (IST), and with `max_lag_days` set it must have been
    fetched within that many days of its session (a daily run); `None` switches the lag limit off for a back-fill."""

    name = "freshness"

    def __init__(self, max_lag_days: int | None):
        if max_lag_days is not None and max_lag_days < 0:
            raise ValueError("max_lag_days cannot be negative")
        self.max_lag = None if max_lag_days is None else timedelta(days=max_lag_days)

    def problem(self, candidate: Candidate) -> str | None:
        fetched_on = candidate.copy.fetched_at.astimezone(IST).date()
        if candidate.day > fetched_on:
            return f"{candidate.filename}: claims session {candidate.day} but was fetched on {fetched_on}"
        if self.max_lag is not None and fetched_on - candidate.day > self.max_lag:
            return (
                f"{candidate.filename}: fetched {fetched_on}, more than {self.max_lag.days} days after {candidate.day}"
            )
        return None
