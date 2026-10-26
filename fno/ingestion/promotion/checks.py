"""The promotion checks (docs/PIPELINE_DESIGN.md, "Promotion checks"): each looks at one staged copy and returns the
reason it must not become a record, or None. The gate runs all of them; a file is promoted only when none objects.
Idempotency (the record already holds the file) is the gate's own step, as it needs the record."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
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


class ContentDayCheck(PromotionCheck):
    """Identity, fail-closed: every date the file itself carries must equal the session its path claims. A file for
    another session, with no dated rows, or whose date cannot be read, is not promoted. No numeric window."""

    name = "content day"

    def __init__(self, content_days: Callable[[str, bytes], set[date]]):
        """`content_days(filename, data)`: the dates in the file's own rows (ValueError when unreadable)."""
        self.content_days = content_days

    def problem(self, candidate: Candidate) -> str | None:
        try:
            days = self.content_days(candidate.filename, candidate.copy.data)
        except ValueError as exc:
            return str(exc)
        if not days:
            return f"{candidate.filename}: the file carries no date"
        if days != {candidate.day}:
            found = ", ".join(str(day) for day in sorted(days))
            return f"{candidate.filename}: the file is dated {found}, its path says {candidate.day}"
        return None


class FreshnessCheck(PromotionCheck):
    """The seam for the owner's numeric window (open decision 1; docs/PIPELINE_DESIGN.md): off unless `config.yaml`
    sets `promotion.max_lag_days`. When on, a file cannot be for a session after the day it was fetched (IST) and must
    have been fetched within that many days of its session."""

    name = "freshness"

    def __init__(self, max_lag_days: int):
        if isinstance(max_lag_days, bool) or not isinstance(max_lag_days, int) or max_lag_days < 0:
            raise ValueError(f"promotion.max_lag_days must be a whole number of days, 0 or more: {max_lag_days!r}")
        self.max_lag = timedelta(days=max_lag_days)

    def problem(self, candidate: Candidate) -> str | None:
        fetched_on = candidate.copy.fetched_at.astimezone(IST).date()
        if candidate.day > fetched_on:
            return f"{candidate.filename}: claims session {candidate.day} but was fetched on {fetched_on}"
        if fetched_on - candidate.day > self.max_lag:
            return (
                f"{candidate.filename}: fetched {fetched_on}, more than {self.max_lag.days} days after {candidate.day}"
            )
        return None
