from datetime import UTC, datetime

import pytest

from fno.ingestion.promotion.checks import Candidate, FreshnessCheck, SchemaCheck
from fno.ingestion.promotion.staging import StagedCopy
from tests.ingestion.promotion.conftest import THURSDAY, moment

NAME = "f.csv"


def candidate(data=b"x", fetched_at=None, day=THURSDAY):
    return Candidate(StagedCopy("nse", fetched_at or moment(day), "p/f.csv", data), day, NAME)


def validator(filename, data):
    if data != b"x":
        raise ValueError(f"{filename}: bad content")


def test_schema_check_passes_good_and_names_the_problem_for_bad_and_empty():
    check = SchemaCheck(validator)
    assert check.problem(candidate(b"x")) is None
    assert check.problem(candidate(b"garbage")) == "f.csv: bad content"
    assert check.problem(candidate(b"")) == "f.csv: bad content"


def test_freshness_same_day_and_the_lag_boundary():
    check = FreshnessCheck(max_lag_days=2)
    assert check.problem(candidate(fetched_at=moment(THURSDAY))) is None
    assert check.problem(candidate(fetched_at=moment(THURSDAY.replace(day=24)))) is None  # exactly 2 days: allowed
    assert "more than 2 days" in check.problem(candidate(fetched_at=moment(THURSDAY.replace(day=25))))


def test_freshness_refuses_a_session_after_the_fetch_day():
    assert "claims session" in FreshnessCheck(7).problem(candidate(fetched_at=moment(THURSDAY.replace(day=21))))


def test_freshness_uses_the_ist_day_not_the_utc_day():
    late_utc = datetime(
        2026, 10, 21, 20, 0, tzinfo=UTC
    )  # 01:30 IST on the 22nd: the session 22nd is not yet in the future
    assert FreshnessCheck(0).problem(candidate(fetched_at=late_utc)) is None


def test_a_negative_lag_is_a_mistake():
    with pytest.raises(ValueError):
        FreshnessCheck(-1)
