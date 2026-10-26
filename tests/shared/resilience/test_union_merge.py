"""Two jobs that append to the same transition log at once must keep both rows (real git, merge=union)."""

import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fno.shared.resilience.transition_log import Transition, TransitionLog

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def git(cwd, *args):
    who = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t"}
    env = {**who, "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(cwd)}
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *args], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True)  # fmt: skip


def test_two_branches_appending_to_the_same_log_merge_without_conflict_or_loss(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    shutil.copy(ROOT / ".gitattributes", tmp_path / ".gitattributes")
    log = TransitionLog(tmp_path / "research/data/resilience/nse.csv")
    log.append(Transition(datetime(2026, 10, 27, 9, 0, tzinfo=UTC), "nse", "opened", 900.0))
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "job-a")
    log.append(Transition(datetime(2026, 10, 27, 9, 20, tzinfo=UTC), "nse", "half_open", 900.0))
    git(tmp_path, "commit", "-qam", "a")
    git(tmp_path, "checkout", "-q", "main")
    git(tmp_path, "checkout", "-q", "-b", "job-b")
    log.append(Transition(datetime(2026, 10, 27, 9, 30, tzinfo=UTC), "nse", "closed", 900.0))
    git(tmp_path, "commit", "-qam", "b")
    git(tmp_path, "merge", "-q", "--no-edit", "job-a")  # raises (check=True) if git reports a conflict
    assert [t.event for t in log.rows("nse")] == ["opened", "half_open", "closed"]
