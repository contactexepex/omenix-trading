"""The shipped default per dataset (docs/stories/P1-staging-record-split.md): a file for another session, with no
date or with an unreadable date is rejected; the correct file is promoted. Real content checks, synthetic layouts."""

from __future__ import annotations

from datetime import timedelta

import pytest

from fno.ingestion.promotion.checks import Candidate, ContentDayCheck, FreshnessCheck
from fno.ingestion.promotion.datasets import PROMOTABLE, equity_content_days, fo_content_days
from fno.ingestion.promotion.gate import PromotionGate, Verdict
from fno.ingestion.promotion.staging import StagedCopy, StagingArea
from fno.ingestion.promotion.wiring import checks_for
from fno.ingestion.storage.wiring import coverage_datasets
from tests.ingestion.promotion.conftest import THURSDAY, WEDNESDAY, moment
from tests.ingestion.promotion.samples import equity_file, fo_udiff_file, participant_file

DAY, OTHER = THURSDAY, WEDNESDAY


def validator(dataset):
    return next(d.validate for d in coverage_datasets() if d.source is PROMOTABLE[dataset].source)


def promote(dataset, data, staging_store, record_store, day=DAY, lag=None):
    source = PROMOTABLE[dataset].source
    gate = PromotionGate(StagingArea(staging_store), record_store, "nse", checks_for(dataset, validator(dataset), lag))
    StagingArea(staging_store).stage("nse", source.path_for(day), data, moment(day))
    return gate.promote(source.path_for(day), day, source.filename_for(day))


def wrong_day_and_undated(dataset):
    """(good bytes, wrong-session bytes, undated bytes) for a dataset, all in its real layout."""
    if dataset in ("participant-oi", "participant-volume"):
        return participant_file(DAY), participant_file(OTHER), participant_file(DAY, title="Participant wise OI")
    if dataset == "fo-bhavcopy":
        return fo_udiff_file(DAY, DAY), fo_udiff_file(OTHER), fo_udiff_file()
    return equity_file(DAY, DAY), equity_file(OTHER), equity_file()


FILE_CHECKED_DATASETS = ["participant-oi", "participant-volume", "fo-bhavcopy", "cm-bhavcopy"]


@pytest.mark.parametrize("dataset", FILE_CHECKED_DATASETS)
def test_the_correct_file_is_promoted(dataset, staging_store, record_store):
    good, _, _ = wrong_day_and_undated(dataset)
    assert promote(dataset, good, staging_store, record_store).verdict is Verdict.PROMOTED
    assert record_store.saved


@pytest.mark.parametrize("dataset", FILE_CHECKED_DATASETS)
def test_a_file_for_another_session_is_rejected(dataset, staging_store, record_store):
    _, wrong, _ = wrong_day_and_undated(dataset)
    assert promote(dataset, wrong, staging_store, record_store).verdict is Verdict.REJECTED
    assert record_store.saved == []


@pytest.mark.parametrize("dataset", FILE_CHECKED_DATASETS)
def test_an_undated_file_is_rejected(dataset, staging_store, record_store):
    _, _, undated = wrong_day_and_undated(dataset)
    assert promote(dataset, undated, staging_store, record_store).verdict is Verdict.REJECTED
    assert record_store.saved == []


@pytest.mark.parametrize("data", [b"", b"<html>blocked</html>"])
@pytest.mark.parametrize("dataset", sorted(PROMOTABLE))
def test_garbage_and_empty_files_are_rejected_by_every_promotable_dataset(dataset, data, staging_store, record_store):
    assert promote(dataset, data, staging_store, record_store).verdict is Verdict.REJECTED
    assert record_store.saved == []


def test_a_file_with_one_row_from_another_day_is_rejected_whole(staging_store, record_store):
    mixed = fo_udiff_file(DAY, OTHER)
    assert promote("fo-bhavcopy", mixed, staging_store, record_store).verdict is Verdict.REJECTED


def test_no_numeric_window_by_default_so_a_late_back_fill_of_the_right_session_is_promoted(staging_store, record_store):
    source = PROMOTABLE["participant-oi"].source
    old = DAY - timedelta(days=400)
    StagingArea(staging_store).stage("nse", source.path_for(old), participant_file(old), moment(DAY))
    gate = PromotionGate(
        StagingArea(staging_store), record_store, "nse", checks_for("participant-oi", validator("participant-oi"))
    )
    assert gate.promote(source.path_for(old), old, source.filename_for(old)).verdict is Verdict.PROMOTED


@pytest.mark.parametrize(("lag", "verdict"), [(None, Verdict.PROMOTED), (3, Verdict.PROMOTED), (1, Verdict.REJECTED)])
def test_a_configured_window_is_applied_and_the_default_has_none(lag, verdict, staging_store, record_store):
    source = PROMOTABLE["participant-oi"].source
    StagingArea(staging_store).stage(
        "nse", source.path_for(DAY), participant_file(DAY), moment(DAY + timedelta(days=3))
    )
    checks = checks_for("participant-oi", validator("participant-oi"), lag)
    gate = PromotionGate(StagingArea(staging_store), record_store, "nse", checks)
    assert gate.promote(source.path_for(DAY), DAY, source.filename_for(DAY)).verdict is verdict


def test_promotable_datasets_are_exactly_the_five_in_the_story():
    assert sorted(PROMOTABLE) == ["cm-bhavcopy", "fii-stats", "fo-bhavcopy", "participant-oi", "participant-volume"]


def test_the_row_date_readers_return_the_rows_dates():
    assert fo_content_days("BhavCopy_NSE_FO_0_0_0_20261022_F_0000.csv.zip", fo_udiff_file(DAY)) == {DAY}
    assert equity_content_days("BhavCopy_NSE_CM_0_0_0_20261022_F_0000.csv.zip", equity_file(DAY)) == {DAY}


def test_an_unreadable_date_is_reported_as_the_reason():
    def unreadable(name, data):
        raise ValueError("x: bad date")

    copy = StagedCopy("nse", moment(DAY), "p/x.csv", b"")
    assert ContentDayCheck(unreadable).problem(Candidate(copy, DAY, "x.csv")) == "x: bad date"


def test_the_freshness_seam_rejects_a_non_number():
    for bad in (True, "7", -1, 1.5):
        with pytest.raises(ValueError):
            FreshnessCheck(bad)


def test_fii_stats_identity_is_the_titles_date_checked_by_its_content_check():
    from fno.ingestion.research_data.fii_derivative_stats import parse_fii_rows
    from fno.shared.fo_bhavcopy import BadFile

    title = "FII DERIVATIVES STATISTICS FOR 22-Oct-2026"
    with pytest.raises(BadFile, match="the title says 22-Oct-2026"):
        parse_fii_rows([[title]], "f.xls", OTHER)
    with pytest.raises(BadFile, match="no 'FII DERIVATIVES STATISTICS FOR"):
        parse_fii_rows([["a sheet with no date"]], "f.xls", DAY)
    with pytest.raises(BadFile, match="no row for"):  # the title passed: only the missing body stops it
        parse_fii_rows([[title]], "f.xls", DAY)


def test_a_file_whose_reader_finds_no_dates_is_rejected():
    copy = StagedCopy("nse", moment(DAY), "p/x.csv", b"")
    assert (
        ContentDayCheck(lambda name, data: set()).problem(Candidate(copy, DAY, "x.csv"))
        == "x.csv: the file carries no date"
    )
