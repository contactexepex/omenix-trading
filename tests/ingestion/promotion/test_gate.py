from datetime import timedelta

from fno.ingestion.promotion.checks import ExceptionCheck, SchemaCheck, SessionCheck
from fno.ingestion.promotion.gate import PromotionGate, Verdict
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_source import ParticipantOiSource
from tests.ingestion.promotion.conftest import GOOD, SATURDAY, THURSDAY, moment

SOURCE = ParticipantOiSource
PATH, NAME = SOURCE.path_for(THURSDAY), SOURCE.filename_for(THURSDAY)


def validate(filename, data):
    if not data.startswith(b"good"):
        raise ValueError(f"{filename}: not a good file")


def gate_for(staging_store, record_store, sink, extra=()):
    staging = StagingArea(staging_store)
    return staging, PromotionGate(staging, record_store, "nse", [SchemaCheck(validate), *extra], sink)


def promote(gate, path=PATH, day=THURSDAY, name=NAME):
    return gate.promote(path, day, name)


def test_a_good_staged_file_is_promoted_to_the_record(staging_store, record_store, sink):
    staging, gate = gate_for(staging_store, record_store, sink)
    staging.stage("nse", PATH, GOOD, moment(THURSDAY))
    assert promote(gate).verdict is Verdict.PROMOTED
    assert record_store.get(PATH) == GOOD and sink.offered == []


def test_nothing_staged_writes_nothing(staging_store, record_store, sink):
    _, gate = gate_for(staging_store, record_store, sink)
    assert promote(gate).verdict is Verdict.NOT_STAGED
    assert record_store.saved == [] and sink.offered == []


def test_garbage_never_reaches_the_record_and_stays_in_staging(staging_store, record_store, sink):
    staging, gate = gate_for(staging_store, record_store, sink)
    staging.stage("nse", PATH, b"<html>blocked</html>", moment(THURSDAY))
    result = promote(gate)
    assert result.verdict is Verdict.REJECTED and "not a good file" in result.reasons[0]
    assert record_store.saved == [] and len(staging.copies("nse", PATH)) == 1


def test_the_earliest_passing_copy_becomes_the_record_not_the_newest(staging_store, record_store, sink):
    staging, gate = gate_for(staging_store, record_store, sink)
    staging.stage("nse", PATH, b"good first", moment(THURSDAY))
    staging.stage("nse", PATH, b"good second", moment(THURSDAY) + timedelta(hours=1))
    assert promote(gate).verdict is Verdict.PROMOTED
    assert record_store.get(PATH) == b"good first"


def test_a_later_passing_version_goes_to_the_revision_sink_with_its_fetch_time(staging_store, record_store, sink):
    staging, gate = gate_for(staging_store, record_store, sink)
    later = moment(THURSDAY) + timedelta(hours=1)
    staging.stage("nse", PATH, b"good first", moment(THURSDAY))
    staging.stage("nse", PATH, b"good second", later)
    result = promote(gate)
    assert result.revisions == 1 and sink.offered == [(PATH, b"good second", later)]


def test_a_failing_earlier_copy_is_skipped_and_the_first_passing_one_is_recorded(staging_store, record_store, sink):
    staging, gate = gate_for(staging_store, record_store, sink)
    staging.stage("nse", PATH, b"truncated", moment(THURSDAY))
    staging.stage("nse", PATH, b"good one", moment(THURSDAY) + timedelta(hours=1))
    result = promote(gate)
    assert result.verdict is Verdict.PROMOTED and record_store.get(PATH) == b"good one"
    assert result.notes and "not a good file" in result.notes[0]  # the failure is still reported (log only)


def test_a_failing_later_copy_after_a_recorded_one_is_a_note_not_a_rejection(staging_store, record_store, sink):
    staging, gate = gate_for(staging_store, record_store, sink)
    staging.stage("nse", PATH, GOOD, moment(THURSDAY))
    staging.stage("nse", PATH, b"garbage", moment(THURSDAY) + timedelta(hours=1))
    result = promote(gate)
    assert result.verdict is Verdict.PROMOTED and len(result.notes) == 1 and sink.offered == []


def test_promoting_twice_is_idempotent_and_keeps_each_version_once(staging_store, record_store, sink):
    staging, gate = gate_for(staging_store, record_store, sink)
    staging.stage("nse", PATH, b"good first", moment(THURSDAY))
    staging.stage("nse", PATH, b"good second", moment(THURSDAY) + timedelta(hours=1))
    promote(gate)
    again = promote(gate)
    assert again.verdict is Verdict.ALREADY_RECORDED and again.revisions == 0
    assert set(record_store.saved) == {PATH} and len(sink.offered) == 1


def test_a_record_written_elsewhere_is_never_overwritten_and_a_differing_staged_copy_is_a_revision(
    staging_store, record_store, sink
):
    staging, gate = gate_for(staging_store, record_store, sink)
    record_store.put(PATH, b"good, written by the live workflow")
    staging.stage("nse", PATH, GOOD, moment(THURSDAY))
    result = promote(gate)
    assert result.verdict is Verdict.ALREADY_RECORDED and result.revisions == 1
    assert record_store.get(PATH) == b"good, written by the live workflow"


def test_only_the_authoritative_sources_copies_are_promoted(staging_store, record_store, sink):
    staging, gate = gate_for(staging_store, record_store, sink)
    staging.stage("yahoo", PATH, GOOD, moment(THURSDAY))
    assert promote(gate).verdict is Verdict.NOT_STAGED and record_store.saved == []


def test_a_non_session_day_is_never_promoted(staging_store, record_store, sink, calendar):
    path, name = SOURCE.path_for(SATURDAY), SOURCE.filename_for(SATURDAY)
    staging, gate = gate_for(staging_store, record_store, sink, [SessionCheck(calendar, SOURCE)])
    staging.stage("nse", path, GOOD, moment(SATURDAY))
    result = promote(gate, path, SATURDAY, name)
    assert result.verdict is Verdict.REJECTED and "not an NSE session" in result.reasons[0]
    assert record_store.saved == []


def test_a_day_before_the_archive_starts_is_never_promoted(staging_store, record_store, sink, calendar):
    day = SOURCE.first_day - timedelta(days=1)
    staging, gate = gate_for(staging_store, record_store, sink, [SessionCheck(calendar, SOURCE)])
    staging.stage("nse", SOURCE.path_for(day), GOOD, moment(THURSDAY))
    assert promote(gate, SOURCE.path_for(day), day, SOURCE.filename_for(day)).verdict is Verdict.REJECTED


def test_a_day_with_a_sourced_exception_is_never_promoted(staging_store, record_store, sink):
    check = ExceptionCheck({(SOURCE.dataset, THURSDAY): "refused content (A23)"}, SOURCE.dataset)
    staging, gate = gate_for(staging_store, record_store, sink, [check])
    staging.stage("nse", PATH, GOOD, moment(THURSDAY))
    result = promote(gate)
    assert result.verdict is Verdict.REJECTED and "refused content (A23)" in result.reasons[0]
    assert record_store.saved == []


def test_a_record_file_without_its_manifest_row_gets_the_row_on_promote(tmp_path, staging_store, sink):
    """The librarian re-saves a file a stopped run left without its row; the gate does the same (judge 2, S1)."""
    from fno.ingestion.storage.manifest_folder import FingerprintingStore, ManifestFolder
    from fno.ingestion.storage.raw_store import LocalFolderStore

    manifests = ManifestFolder(tmp_path / "manifests")
    plain = LocalFolderStore(tmp_path / "record")
    plain.put(PATH, GOOD)  # saved, but no manifest row
    assert manifests.fingerprints(SOURCE) == {}
    record = FingerprintingStore(plain, manifests, [SOURCE])
    staging, gate = gate_for(staging_store, record, sink)
    staging.stage("nse", PATH, GOOD, moment(THURSDAY))
    assert promote(gate).verdict is Verdict.ALREADY_RECORDED
    assert list(manifests.fingerprints(SOURCE)) == [NAME]


def test_a_manifest_that_disagrees_is_a_conflict_problem_not_a_crash(tmp_path, staging_store, sink):
    from fno.ingestion.storage.manifest_folder import Fingerprint, FingerprintingStore, ManifestFolder
    from fno.ingestion.storage.raw_store import LocalFolderStore

    manifests = ManifestFolder(tmp_path / "manifests")
    manifests.record(SOURCE, Fingerprint(THURSDAY, SOURCE.url_for(PATH), "0" * 64, 5))  # another SHA-256 for the day
    record = FingerprintingStore(LocalFolderStore(tmp_path / "record"), manifests, [SOURCE])
    staging, gate = gate_for(staging_store, record, sink)
    staging.stage("nse", PATH, GOOD, moment(THURSDAY))
    result = promote(gate)
    assert result.verdict is Verdict.CONFLICT and "different SHA-256" in result.reasons[0]


def test_a_held_file_no_passing_copy_proves_is_not_saved_again(staging_store, record_store, sink):
    """Only a passing copy equal to the held bytes justifies the re-save that repairs a manifest row."""
    staging, gate = gate_for(staging_store, record_store, sink)
    record_store.put(PATH, b"good, held")
    record_store.saved.clear()
    staging.stage("nse", PATH, b"good, staged", moment(THURSDAY))
    assert promote(gate).verdict is Verdict.ALREADY_RECORDED
    assert record_store.saved == []


def test_a_record_written_elsewhere_stays_and_an_earlier_different_staged_copy_is_only_a_revision(
    staging_store, record_store, sink
):
    """The Record holds X (the live path wrote it). Staging holds Y first, then X: X stays, Y is a revision, no conflict."""
    staging, gate = gate_for(staging_store, record_store, sink)
    record_store.put(PATH, b"good X")
    staging.stage("nse", PATH, b"good Y", moment(THURSDAY))
    staging.stage("nse", PATH, b"good X", moment(THURSDAY) + timedelta(hours=1))
    result = promote(gate)
    assert result.verdict is Verdict.ALREADY_RECORDED and result.revisions == 1
    assert record_store.get(PATH) == b"good X" and [data for _, data, _ in sink.offered] == [b"good Y"]
