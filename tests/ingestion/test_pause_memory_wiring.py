"""Story R1b2: which commands are live windows, how `main` wires the shared pacer, and that every workflow commits the
pause log in its last step with the record scan on. Static checks over the real files."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from fno.ingestion import cli
from fno.ingestion.pause_memory import attach_pause_memory, command_words, is_live_window
from fno.shared.constants import LIVE_WINDOW_COMMANDS, PAUSE_LOG_PATH, PAUSE_LOG_RUN_PATH
from fno.shared.http_pacing import SHARED_PACER

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
<<<<<<< HEAD
NOT_PACED = {"data-checks.yml", "news-promote.yml", "news-cluster.yml", "staging-cleanup.yml"}  # reach Drive only
=======
NOT_PACED = {
    "data-checks.yml",
    "news-promote.yml",
    "news-cluster.yml",
    "rebuild-receipts.yml",
}  # reach Drive only (no paced host)
>>>>>>> origin/main
STEP = "bash ops/commit_pause_log.sh"

# the set is explicit: adding or removing a live command is a decision, and it fails here first
EXPECTED_LIVE = {
    "quotes record",
    "participant-oi watch",
    "participant-oi check-once",
    "closes read",
    "preopen record",
    "fo-masters",
    "data-snapshot fii-dii-cash-by-session",
    "data-snapshot fpi-daily-by-session",
}


def test_the_live_window_set_is_exactly_the_stated_one():
    assert set(LIVE_WINDOW_COMMANDS) == EXPECTED_LIVE


@pytest.mark.parametrize("words", sorted(w.split() for w in EXPECTED_LIVE))
def test_every_live_command_is_a_real_command(words):
    with pytest.raises(SystemExit) as stopped:
        cli.build_parser().parse_args([*words, "--help"])
    assert stopped.value.code == 0  # --help ran, so the words name a real command


@pytest.mark.parametrize(
    ("argv", "words", "live"),
    [
        (["quotes", "record", "--source", "nse"], ("quotes", "record"), True),
        (["--config", "x.yaml", "participant-oi", "watch"], ("participant-oi", "watch"), True),
        (["fo-masters"], ("fo-masters",), True),
        (["fo-masters", "--help"], ("fo-masters",), True),
        (["data-snapshot", "fii-dii-cash-by-session"], ("data-snapshot", "fii-dii-cash-by-session"), True),
        (["data-snapshot", "equity-list"], ("data-snapshot", "equity-list"), False),
        (["quotes", "record-indices"], ("quotes", "record-indices"), False),
        (["global-cues", "fill"], ("global-cues", "fill"), False),
        (["data-librarian", "index-close"], ("data-librarian", "index-close"), False),
        ([], (), False),
    ],
)
def test_command_words_and_the_live_decision(argv, words, live):
    assert command_words(argv) == words and is_live_window(argv) is live


def test_main_attaches_the_shared_pacer_with_the_two_logs_and_the_live_flag(tmp_path):
    attach_pause_memory(["quotes", "record"], root=tmp_path)
    assert SHARED_PACER.live_window is True
    assert SHARED_PACER.log.path == tmp_path / PAUSE_LOG_RUN_PATH  # it writes only the run-local file
    assert SHARED_PACER.log.committed.path == tmp_path / PAUSE_LOG_PATH
    attach_pause_memory(["global-cues", "fill"], root=tmp_path)
    assert SHARED_PACER.live_window is False


# ---- the workflows ----------------------------------------------------------------------------------------


def steps_of(path):
    document = yaml.safe_load(path.read_text("utf-8"))
    (job,) = document["jobs"].values()
    return job, job["steps"]


@pytest.mark.parametrize("path", [p for p in WORKFLOWS if p.name not in NOT_PACED], ids=lambda p: p.name)
def test_every_paced_workflow_ends_with_the_same_pause_log_step(path):
    job, steps = steps_of(path)
    last = steps[-1]
    assert last["run"] == STEP and last["continue-on-error"] is True  # a lost row fails open, never the run
    assert last["if"] == "${{ always() && !inputs.dry_run }}"
    assert yaml.safe_load(path.read_text("utf-8"))["permissions"]["contents"] == "write"


def test_the_one_workflow_that_never_reaches_a_paced_host_has_no_such_step():
    _, steps = steps_of(ROOT / ".github" / "workflows" / "data-checks.yml")
    assert not any(STEP in str(s.get("run", "")) for s in steps)


def test_the_script_sets_the_hooks_path_and_identity_itself_and_never_skips_the_scan():
    script = (ROOT / "ops" / "commit_pause_log.sh").read_text("utf-8")
    assert "git config core.hooksPath .githooks" in script and "git config user.name" in script
    assert "git config user.email" in script
    assert "--no-verify" not in script and "git add --" in script  # one path only
    assert len(re.findall(r"git add", script)) == 1


def test_the_run_local_directory_is_git_ignored():
    assert "research/data/resilience/.run/" in (ROOT / ".gitignore").read_text("utf-8")


# ---- through main ----------------------------------------------------------------------------------------


class _Parsed:
    def __init__(self):
        self.func = lambda args: 0  # the command itself is patched out


class _Parser:
    def parse_args(self, argv):
        return _Parsed()


@pytest.mark.parametrize(
    ("argv", "live"),
    [(["quotes", "record"], True), (["fo-masters"], True), (["data-librarian", "index-close"], False)],
)
def test_main_wires_the_shared_pacer_before_the_command_runs(monkeypatch, argv, live):
    from fno.shared.resilience.transition_log import LayeredLog

    monkeypatch.setattr(cli, "build_parser", lambda: _Parser())
    assert cli.main(argv) == 0
    assert isinstance(SHARED_PACER.log, LayeredLog) and SHARED_PACER.live_window is live
    assert (
        SHARED_PACER.log.committed.path == ROOT / PAUSE_LOG_PATH and SHARED_PACER.log.path == ROOT / PAUSE_LOG_RUN_PATH
    )


def test_main_reads_sys_argv_when_it_is_given_no_argv(monkeypatch):
    monkeypatch.setattr(cli, "build_parser", lambda: _Parser())
    monkeypatch.setattr("sys.argv", ["fno", "closes", "read"])
    cli.main()
    assert SHARED_PACER.live_window is True
