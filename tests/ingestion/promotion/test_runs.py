from fno.ingestion.promotion.checks import ExceptionCheck, SchemaCheck
from fno.ingestion.promotion.gate import PromotionGate, Verdict
from fno.ingestion.promotion.runs import PromotionRun, Stager
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_source import ParticipantOiSource
from tests.ingestion.promotion.conftest import (
    FRIDAY,
    GOOD,
    SATURDAY,
    THURSDAY,
    WEDNESDAY,
    FakeNse,
    RecordingSink,
    moment,
)

SOURCE = ParticipantOiSource
WEEK = (WEDNESDAY, THURSDAY, FRIDAY)


def stager(source, staging_store, calendar, exceptions=None):
    return Stager(source, StagingArea(staging_store), "nse", calendar, exceptions or {}, clock=lambda: moment(FRIDAY))


def test_the_stager_stages_each_session_and_writes_only_staging(staging_store, record_store, calendar):
    source = FakeNse({SOURCE.path_for(d): GOOD + d.isoformat().encode() for d in WEEK})
    report = stager(source, staging_store, calendar).stage(WEDNESDAY, SATURDAY)  # Saturday is no session
    assert report.staged == list(WEEK) and report.complete
    assert staging_store.saved and all(p.startswith("nse/") for p in staging_store.saved)
    assert record_store.saved == []  # the stager has no way to reach the record


def test_a_second_pass_stages_nothing_new(staging_store, calendar):
    source = FakeNse({SOURCE.path_for(d): GOOD for d in WEEK})
    stager(source, staging_store, calendar).stage(WEDNESDAY, FRIDAY)
    report = stager(source, staging_store, calendar).stage(WEDNESDAY, FRIDAY)
    assert report.staged == [] and report.unchanged == list(WEEK)


def test_not_published_refused_and_excepted_days_are_reported_not_hidden(staging_store, calendar):
    source = FakeNse({SOURCE.path_for(FRIDAY): GOOD}, refused={SOURCE.path_for(THURSDAY)})
    report = stager(source, staging_store, calendar, {(SOURCE.dataset, WEDNESDAY): "never published"}).stage(
        WEDNESDAY, FRIDAY
    )
    assert (report.staged, report.excepted) == ([FRIDAY], 1)
    assert [d for d, _ in report.refused] == [THURSDAY] and not report.complete
    assert "source refused" in "\n".join(report.lines())


def test_a_day_the_source_does_not_publish_is_incomplete(staging_store, calendar):
    report = stager(FakeNse(), staging_store, calendar).stage(THURSDAY, THURSDAY)
    assert report.not_published == [THURSDAY] and not report.complete


def run_for(staging_store, record_store, calendar, validate, exceptions=None):
    exceptions = exceptions or {}
    checks = [SchemaCheck(validate), ExceptionCheck(exceptions, SOURCE.dataset)]
    gate = PromotionGate(StagingArea(staging_store), record_store, "nse", checks, RecordingSink())
    return PromotionRun(gate, SOURCE, calendar, exceptions)


def validate(filename, data):
    if not data.startswith(b"good"):
        raise ValueError(f"{filename}: bad")


def test_end_to_end_stage_then_promote_leaves_bad_days_out_of_the_record(staging_store, record_store, calendar):
    files = {SOURCE.path_for(WEDNESDAY): GOOD, SOURCE.path_for(THURSDAY): b"<html>", SOURCE.path_for(FRIDAY): GOOD}
    stager(FakeNse(files), staging_store, calendar).stage(WEDNESDAY, FRIDAY)
    report = run_for(staging_store, record_store, calendar, validate).promote(WEDNESDAY, FRIDAY)
    assert report.days(Verdict.PROMOTED) == [WEDNESDAY, FRIDAY]
    assert report.days(Verdict.REJECTED) == [THURSDAY] and not report.complete and not report.notes()
    assert record_store.get(SOURCE.path_for(THURSDAY)) is None
    assert any("rejected" in line and str(THURSDAY) in line for line in report.problems())


def test_a_second_promotion_run_changes_nothing(staging_store, record_store, calendar):
    stager(FakeNse({SOURCE.path_for(THURSDAY): GOOD}), staging_store, calendar).stage(THURSDAY, THURSDAY)
    run = run_for(staging_store, record_store, calendar, validate)
    run.promote(THURSDAY, THURSDAY)
    report = run.promote(THURSDAY, THURSDAY)
    assert report.days(Verdict.ALREADY_RECORDED) == [THURSDAY] and report.complete
    assert record_store.saved == [SOURCE.path_for(THURSDAY)]


def test_an_empty_range_is_complete_and_unstaged_days_are_problems(staging_store, record_store, calendar):
    run = run_for(staging_store, record_store, calendar, validate)
    assert run.promote(SATURDAY, SATURDAY).complete  # no session in the range
    missing = run.promote(THURSDAY, THURSDAY)
    assert missing.days(Verdict.NOT_STAGED) == [THURSDAY] and not missing.complete


def test_a_failing_copy_on_a_day_the_record_holds_is_a_note_not_a_problem(staging_store, record_store, calendar):
    area = StagingArea(staging_store)
    path = SOURCE.path_for(THURSDAY)
    area.stage("nse", path, GOOD, moment(THURSDAY))
    area.stage("nse", path, b"<html>", moment(THURSDAY).replace(hour=15))
    report = run_for(staging_store, record_store, calendar, validate).promote(THURSDAY, THURSDAY)
    assert report.complete and report.problems() == [] and len(report.notes()) == 1


def test_a_failing_copy_is_reported_again_while_the_record_lacks_the_day_and_not_outside_the_range(
    staging_store, record_store, calendar
):
    StagingArea(staging_store).stage("nse", SOURCE.path_for(THURSDAY), b"<html>", moment(THURSDAY))
    run = run_for(staging_store, record_store, calendar, validate)
    assert run.promote(THURSDAY, THURSDAY).problems() and run.promote(THURSDAY, THURSDAY).problems()
    assert run.promote(FRIDAY, FRIDAY).problems() == [f"not staged {FRIDAY}"]  # only the range asked for is examined
    assert run.promote(WEDNESDAY, WEDNESDAY).results[0][0] == WEDNESDAY


def test_an_excepted_day_with_nothing_staged_is_counted_not_a_problem_and_with_a_file_it_is_refused(
    staging_store, record_store, calendar
):
    exceptions = {(SOURCE.dataset, THURSDAY): "never published (A1)"}
    run = run_for(staging_store, record_store, calendar, validate, exceptions)
    quiet = run.promote(THURSDAY, THURSDAY)
    assert quiet.excepted == 1 and quiet.complete
    StagingArea(staging_store).stage("nse", SOURCE.path_for(THURSDAY), GOOD, moment(THURSDAY))
    assert run.promote(THURSDAY, THURSDAY).days(Verdict.REJECTED) == [THURSDAY]
    assert record_store.saved == []


def test_a_stager_cannot_be_given_a_record_store(record_store, calendar):
    import pytest

    with pytest.raises(TypeError, match="StagingArea"):
        Stager(FakeNse(), record_store, "nse", calendar, {})
