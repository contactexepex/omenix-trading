"""Story R1b2: a run reads the committed pause log and writes only its own local file."""

from datetime import UTC, datetime

from fno.shared.resilience.transition_log import OPENED, LayeredLog, Transition, TransitionLog

T0 = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)


def test_reads_both_files_in_time_order_and_writes_only_the_local_one(tmp_path):
    committed, local = tmp_path / "paced-hosts.csv", tmp_path / ".run" / "paced-hosts.csv"
    TransitionLog(committed).append(Transition(T0, "paced:a", OPENED, 900.0))
    before = committed.read_text()
    log = LayeredLog(committed, local)
    later = Transition(T0.replace(minute=30), "paced:a", "closed", 900.0)
    log.append(later)
    assert committed.read_text() == before  # the tracked file is never touched during a run
    assert local.is_file() and [r.event for r in log.rows("paced:a")] == [OPENED, "closed"]
    assert log.last("paced:a") == later


def test_a_missing_committed_file_and_an_empty_history_read_as_no_rows(tmp_path):
    log = LayeredLog(tmp_path / "none.csv", tmp_path / "run" / "none.csv")
    assert log.rows("paced:a") == [] and log.last("paced:a") is None
