"""Story R1b2: the last workflow step, run for real against throwaway git repositories (a bare origin and clones). It
proves the reason for the run-local file: a tracked file modified during the run would make another committer's
`git pull --no-rebase` refuse, and the step merges the rows only after its own pull."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops" / "commit_pause_log.sh"
LOG, LOCAL = "research/data/resilience/paced-hosts.csv", "research/data/resilience/.run/paced-hosts.csv"
HEADER = "at,source,event,cool_down_seconds"
ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.org",
    "HOME": "/nonexistent",
    "PATH": "/usr/bin:/bin:/usr/local/bin",
}


def git(cwd, *args, check=True):
    done = subprocess.run(["git", *args], cwd=cwd, env=ENV, capture_output=True, text=True)
    if check and done.returncode:
        raise AssertionError(f"git {args}: {done.stderr}")
    return done


def row(minute, source="paced:www.nseindia.com", event="opened"):
    return f"2026-10-27T09:{minute:02d}:00+00:00,{source},{event},900.0"


@pytest.fixture
def repos(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", "-q", str(origin), str(seed))
    (seed / ".gitignore").write_text("research/data/resilience/.run/\n")
    git(seed, "add", ".")
    git(seed, "commit", "-q", "-m", "seed")
    git(seed, "push", "-q", "origin", "HEAD:main")
    clones = {}
    for name in "ab":
        git(tmp_path, "clone", "-q", str(origin), str(tmp_path / name))
        clones[name] = tmp_path / name
    return origin, clones


def write_local(clone, *rows):
    path = clone / LOCAL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([HEADER, *rows]) + "\n")


def run_step(clone):
    return subprocess.run(["bash", str(SCRIPT)], cwd=clone, env=ENV, capture_output=True, text=True)


def committed_log(origin, tmp_path):
    check = tmp_path / "check"
    if check.exists():
        git(check, "pull", "-q", "origin", "main")
    else:
        git(tmp_path, "clone", "-q", str(origin), str(check))
    path = check / LOG
    return path.read_text().splitlines() if path.is_file() else []


def test_a_run_with_no_transitions_commits_nothing(repos, tmp_path):
    origin, clones = repos
    assert run_step(clones["a"]).returncode == 0
    assert committed_log(origin, tmp_path) == []


def test_the_rows_reach_the_committed_log_with_the_header_once(repos, tmp_path):
    origin, clones = repos
    write_local(clones["a"], row(1), row(2, event="closed"))
    done = run_step(clones["a"])
    assert done.returncode == 0, done.stderr
    assert committed_log(origin, tmp_path) == [HEADER, row(1), row(2, event="closed")]
    assert not (clones["a"] / LOCAL).exists()  # merged, so removed


def test_a_second_run_appends_only_its_new_rows_and_never_a_second_header(repos, tmp_path):
    origin, clones = repos
    write_local(clones["a"], row(1))
    run_step(clones["a"])
    write_local(clones["b"], row(1), row(5, event="closed"))  # b repeats a row a has already merged
    assert run_step(clones["b"]).returncode == 0
    assert committed_log(origin, tmp_path) == [HEADER, row(1), row(5, event="closed")]


def test_a_manifest_committers_pull_still_works_while_the_run_has_pending_rows(repos, tmp_path):
    """The reason for the run-local file. Run `a` has a pending transition and another workflow pushes the same log."""
    origin, clones = repos
    a, b = clones["a"], clones["b"]
    write_local(b, row(3))
    run_step(b)  # another workflow pushes the committed log
    write_local(a, row(1))  # a's run has a pending transition in the ignored file
    pulled = git(a, "pull", "--no-rebase", "--no-edit", "origin", "main", check=False)  # a manifest committer's pull
    assert pulled.returncode == 0, pulled.stderr
    assert run_step(a).returncode == 0
    assert committed_log(origin, tmp_path) == [HEADER, row(3), row(1)]


def test_the_old_design_would_have_refused_that_pull(repos):
    """Writing the tracked file during the run (the design judge 2 refused) makes the same pull fail."""
    _, clones = repos
    a, b = clones["a"], clones["b"]
    for clone, minute in ((a, 1), (b, 3)):
        (clone / LOG).parent.mkdir(parents=True, exist_ok=True)
        (clone / LOG).write_text(HEADER + "\n" + row(minute) + "\n")
    git(b, "add", LOG)
    git(b, "commit", "-q", "-m", "rows")
    git(b, "push", "-q", "origin", "HEAD:main")
    git(a, "add", "-N", LOG)  # a tracked-but-dirty log, as an appended-to tracked file would be
    pulled = git(a, "pull", "--no-rebase", "--no-edit", "origin", "main", check=False)
    assert pulled.returncode != 0


def test_a_failed_pull_leaves_the_rows_for_the_next_try_and_fails_loudly(repos):
    _, clones = repos
    a = clones["a"]
    write_local(a, row(1))
    git(a, "remote", "set-url", "origin", "/nonexistent/origin.git")
    assert run_step(a).returncode != 0 and (a / LOCAL).exists()  # nothing lost; the workflow marks it continue-on-error


def test_a_tracked_log_modified_during_the_run_is_refused_too(repos):
    """The same reproduction with the log already tracked and then edited in place, as an appending run would."""
    _, clones = repos
    a, b = clones["a"], clones["b"]
    (a / LOG).parent.mkdir(parents=True, exist_ok=True)
    (a / LOG).write_text(HEADER + "\n")
    git(a, "add", LOG)
    git(a, "commit", "-q", "-m", "log")
    git(a, "push", "-q", "origin", "HEAD:main")
    git(b, "pull", "-q", "origin", "main")
    (b / LOG).write_text(HEADER + "\n" + row(3) + "\n")
    git(b, "commit", "-q", "-am", "b's rows")
    git(b, "push", "-q", "origin", "HEAD:main")
    (a / LOG).write_text(HEADER + "\n" + row(1) + "\n")  # a's run appended to the tracked file
    pulled = git(a, "pull", "--no-rebase", "--no-edit", "origin", "main", check=False)
    assert pulled.returncode != 0 and "overwritten" in pulled.stderr
