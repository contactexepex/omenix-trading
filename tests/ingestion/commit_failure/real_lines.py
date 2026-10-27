"""The three lines the REAL manifest committer returns, made in a throw-away git repository: a commit that was pushed,
a run with nothing new to commit, and a commit whose pull or push failed. Tests of the commit-failure signalling use
these, never a string written by hand, so a change in the committer's wording cannot leave a test passing against an
invented line."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from fno.ingestion.storage.manifest_commit import GitManifestRecorder


@dataclass(frozen=True)
class RealLines:
    pushed: str
    nothing: str
    failed: str


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def real_lines(tmp_path: Path) -> RealLines:
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com"), ("core.hooksPath", "/dev/null")):
        _git(work, "config", key, value)
    (work / "README").write_text("x")
    _git(work, "add", "README")
    _git(work, "commit", "-q", "-m", "init")
    _git(work, "push", "-q", "origin", "HEAD:main")
    recorder = GitManifestRecorder(work, work / "manifests")
    nothing = recorder.commit("test")
    (work / "manifests").mkdir()
    (work / "manifests" / "a.csv").write_text("row\n")
    pushed = recorder.commit("test")
    _git(work, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
    (work / "manifests" / "b.csv").write_text("row\n")
    return RealLines(pushed, nothing, recorder.commit("test"))
