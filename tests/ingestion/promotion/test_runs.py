from fno.ingestion.promotion.checks import SchemaCheck
from fno.ingestion.promotion.gate import PromotionGate, Verdict
from fno.ingestion.promotion.runs import PromotionRun, Stager
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_source import ParticipantOiSource
from tests.ingestion.promotion.conftest import FRIDAY, GOOD, SATURDAY, THURSDAY, WEDNESDAY, FakeNse, moment

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


def run_for(staging_store, record_store, calendar, validate):
    gate = PromotionGate(StagingArea(staging_store), record_store, "nse", [SchemaCheck(validate)])
    return PromotionRun(gate, SOURCE, calendar, {})


def validate(filename, data):
    if not data.startswith(b"good"):
        raise ValueError(f"{filename}: bad")


def test_end_to_end_stage_then_promote_leaves_bad_days_out_of_the_record(staging_store, record_store, calendar):
    files = {SOURCE.path_for(WEDNESDAY): GOOD, SOURCE.path_for(THURSDAY): b"<html>", SOURCE.path_for(FRIDAY): GOOD}
    stager(FakeNse(files), staging_store, calendar).stage(WEDNESDAY, FRIDAY)
    report = run_for(staging_store, record_store, calendar, validate).promote(WEDNESDAY, FRIDAY)
    assert report.days(Verdict.PROMOTED) == [WEDNESDAY, FRIDAY]
    assert report.days(Verdict.REJECTED) == [THURSDAY] and not report.complete
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
