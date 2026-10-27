"""CF1: the one definition of "this commit failed"; the seven callers that read the line ask it."""

from __future__ import annotations

import pytest

from fno.ingestion.circulars import job as circulars_job
from fno.ingestion.close_read import cli as close_read_cli
from fno.ingestion.flow_history import cli as flow_history_cli
from fno.ingestion.fo_masters import job as fo_masters_job
from fno.ingestion.global_cues import preopen_cli
from fno.ingestion.preopen import record as preopen_record
from fno.ingestion.storage import manifest_commit, repair_cli
from fno.ingestion.storage.manifest_commit import NOT_COMMITTED_MARK, commit_failed, exit_for_commit
from tests.ingestion.commit_failure.real_lines import real_lines


@pytest.fixture(scope="module")
def lines(tmp_path_factory):
    return real_lines(tmp_path_factory.mktemp("real"))


def test_only_the_real_failure_line_is_a_failure_not_a_push_and_not_an_empty_diff(lines):
    """No false-red: a run with nothing new to commit is the commonest healthy outcome."""
    assert commit_failed(lines.failed)
    assert not commit_failed(lines.pushed) and not commit_failed(lines.nothing)
    assert not commit_failed("") and not commit_failed("committed and pushed (0 file(s))")


def test_other_lines_that_say_not_are_not_this_failure():
    """Only the committer's own "NOT committed" counts. The intraday sync's foreign-staged line has its own once-per-run
    alert, and other commands print "NOT archived" or "NOT promoted" for other reasons; none may turn a run red here."""
    assert not commit_failed(
        "manifest rows NOT pulled or committed: 2 file(s) staged that are not the recorder's: a, b"
    )
    assert not commit_failed("NOT archived: bad day") and not commit_failed("files were NOT promoted to the record")
    assert not commit_failed("not committed")  # the lower-case phrase is not the committer's


def test_the_mark_is_read_from_the_message_template():
    assert NOT_COMMITTED_MARK == " NOT committed"
    assert NOT_COMMITTED_MARK in manifest_commit.NOT_COMMITTED.format(label="x", step="push", reason="r", folder="f")


def test_exit_for_commit_leaves_a_good_commit_alone_and_alerts_exactly_once_for_a_failed_one(lines):
    sent = []
    assert exit_for_commit([lines.pushed], 0, sent.append, "x") == 0
    assert exit_for_commit([lines.nothing], 1, sent.append, "x") == 1 and sent == []
    assert exit_for_commit([lines.failed, lines.failed], 0, sent.append, "x") == 1 and len(sent) == 1
    assert exit_for_commit([lines.failed], 2, sent.append, "x") == 2  # never lowers a worse code


def test_the_alert_names_the_command_and_carries_no_row(lines):
    sent = []
    exit_for_commit([lines.failed + " | secret-row-123"], 0, sent.append, "data-librarian nse-fo")
    assert "data-librarian nse-fo" in sent[0] and "secret-row-123" not in sent[0] and "manifests/" not in sent[0]


@pytest.mark.parametrize(
    "module",
    [close_read_cli, circulars_job, fo_masters_job, preopen_cli, repair_cli, preopen_record, flow_history_cli],
)
def test_no_caller_keeps_its_own_copy_of_the_failure_marker(module):
    """P5b: the seven callers that used to keep their own string now ask `commit_failed`, so a changed message cannot
    silently disable one (their behaviour is pinned in test_callers.py)."""
    assert not [name for name in vars(module) if name.startswith("NOT_COMMITTED") and name != "NOT_COMMITTED_MARK"]
    assert getattr(module, "NOT_COMMITTED_MARK", NOT_COMMITTED_MARK) is NOT_COMMITTED_MARK
