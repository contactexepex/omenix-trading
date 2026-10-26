from datetime import timedelta

from fno.ingestion.promotion.checks import FreshnessCheck, SchemaCheck
from fno.ingestion.promotion.gate import PromotionGate, Verdict
from fno.ingestion.promotion.staging import StagingArea
from tests.ingestion.promotion.conftest import GOOD, THURSDAY, moment

PATH, NAME = "nse/derivatives/participant-oi/2026/10/f.csv", "f.csv"


def validate(filename, data):
    if not data.startswith(b"good"):
        raise ValueError(f"{filename}: not a good file")


def gate_for(staging_store, record_store, lag=7):
    staging = StagingArea(staging_store)
    checks = [FreshnessCheck(lag), SchemaCheck(validate)]
    return staging, PromotionGate(staging, record_store, "nse", checks)


def promote(gate):
    return gate.promote(PATH, THURSDAY, NAME)


def test_a_good_staged_file_is_promoted_to_the_record(staging_store, record_store):
    staging, gate = gate_for(staging_store, record_store)
    staging.stage("nse", PATH, GOOD, moment(THURSDAY))
    assert promote(gate).verdict is Verdict.PROMOTED
    assert record_store.get(PATH) == GOOD


def test_nothing_staged_writes_nothing(staging_store, record_store):
    _, gate = gate_for(staging_store, record_store)
    assert promote(gate).verdict is Verdict.NOT_STAGED
    assert record_store.saved == []


def test_garbage_never_reaches_the_record_and_stays_in_staging(staging_store, record_store):
    staging, gate = gate_for(staging_store, record_store)
    staging.stage("nse", PATH, b"<html>blocked</html>", moment(THURSDAY))
    result = promote(gate)
    assert result.verdict is Verdict.REJECTED and "not a good file" in result.reasons[0]
    assert record_store.saved == [] and record_store.get(PATH) is None
    assert len(staging.copies("nse", PATH)) == 1


def test_a_stale_fetch_is_rejected_even_when_the_content_is_good(staging_store, record_store):
    staging, gate = gate_for(staging_store, record_store, lag=1)
    staging.stage("nse", PATH, GOOD, moment(THURSDAY) + timedelta(days=5))
    assert promote(gate).verdict is Verdict.REJECTED
    assert record_store.saved == []


def test_a_bad_newest_copy_falls_back_to_an_older_good_one(staging_store, record_store):
    staging, gate = gate_for(staging_store, record_store)
    staging.stage("nse", PATH, GOOD, moment(THURSDAY))
    staging.stage("nse", PATH, b"truncated", moment(THURSDAY) + timedelta(hours=1))
    assert promote(gate).verdict is Verdict.PROMOTED
    assert record_store.get(PATH) == GOOD


def test_promoting_twice_is_idempotent(staging_store, record_store):
    staging, gate = gate_for(staging_store, record_store)
    staging.stage("nse", PATH, GOOD, moment(THURSDAY))
    promote(gate)
    assert promote(gate).verdict is Verdict.ALREADY_RECORDED
    assert record_store.saved == [PATH]


def test_a_different_good_file_never_overwrites_the_record(staging_store, record_store):
    staging, gate = gate_for(staging_store, record_store)
    record_store.put(PATH, b"good, first version")
    staging.stage("nse", PATH, GOOD, moment(THURSDAY))
    assert promote(gate).verdict is Verdict.DIFFERS_FROM_RECORD
    assert record_store.get(PATH) == b"good, first version"


def test_only_the_authoritative_sources_copies_are_promoted(staging_store, record_store):
    staging, gate = gate_for(staging_store, record_store)
    staging.stage("yahoo", PATH, GOOD, moment(THURSDAY))
    assert promote(gate).verdict is Verdict.NOT_STAGED
    assert record_store.saved == []
