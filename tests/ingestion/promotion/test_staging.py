from datetime import timedelta

import pytest

from fno.ingestion.promotion.staging import StagingArea, stamp_of
from tests.ingestion.promotion.conftest import THURSDAY, moment

PATH = "nse/derivatives/participant-oi/2026/10/f.csv"


def test_stage_then_read_back_with_source_and_fetch_time(staging_store):
    area = StagingArea(staging_store)
    assert area.stage("nse", PATH, b"one", moment(THURSDAY)) is True
    (copy,) = area.copies("nse", PATH)
    assert (copy.source, copy.fetched_at, copy.path, copy.data) == ("nse", moment(THURSDAY), PATH, b"one")
    assert staging_store.saved == [f"nse/{stamp_of(moment(THURSDAY))}/{PATH}"]


def test_same_bytes_again_is_not_a_second_copy(staging_store):
    area = StagingArea(staging_store)
    area.stage("nse", PATH, b"one", moment(THURSDAY))
    assert area.stage("nse", PATH, b"one", moment(THURSDAY) + timedelta(hours=1)) is False
    assert len(area.copies("nse", PATH)) == 1


def test_newer_fetch_is_a_new_copy_listed_after_the_old_one_which_stays(staging_store):
    area = StagingArea(staging_store)
    area.stage("nse", PATH, b"old", moment(THURSDAY))
    area.stage("nse", PATH, b"new", moment(THURSDAY) + timedelta(hours=1))
    assert [c.data for c in area.copies("nse", PATH)] == [b"old", b"new"]  # earliest fetch first
    assert area.latest("nse", PATH).data == b"new"
    assert area.latest("nse", "nse/other/path.csv") is None


def test_empty_staging_and_other_sources_and_stray_folders(staging_store):
    area = StagingArea(staging_store)
    assert area.copies("nse", PATH) == []
    area.stage("bse", PATH, b"x", moment(THURSDAY))
    staging_store.store.put("nse/not-a-time/" + PATH, b"stray")
    assert area.copies("nse", PATH) == []


@pytest.mark.parametrize("source", ["", "..", "a/../b", "/abs"])
def test_a_bad_source_tag_is_refused(staging_store, source):
    with pytest.raises(ValueError):
        StagingArea(staging_store).stage(source, PATH, b"x", moment(THURSDAY))
