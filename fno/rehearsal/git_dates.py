"""A rehearsal's commits are dated by its replay clock (story REH1b): D3's late rule compares a decision's commit time
with the 15:15 snapshot, and G13b's seals compare push times with 15:30, so a commit dated by the wall clock (the day
after) would be judged wrongly. A `git` shim first on the rehearsal's `PATH` sets both dates from the shared clock
file, then runs the real git: every git call of every step goes through it, as O2's harness dates them by its fake
clock (`GIT_COMMITTER_DATE`)."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

from .clock import OFFSET_FILE

SHIM = """#!/bin/sh
# Story REH1b: this rehearsal's git, dated by its replay clock (the real git: {git})
offset=$(cat '{offset}')
stamp=$(awk -v t="$(date +%s.%N)" -v o="$offset" 'BEGIN {{ printf "%d", t + o }}')
GIT_COMMITTER_DATE="$stamp +0000" GIT_AUTHOR_DATE="$stamp +0000" exec '{git}' "$@"
"""
NO_GIT = "rehearsal: no git found on PATH outside the rehearsal's own folder"


def install_git_shim(folder: Path, state: Path, path: str = os.environ.get("PATH", "")) -> str:
    """Writes the shim into `folder` and returns the PATH that puts it first."""
    folder.mkdir(parents=True, exist_ok=True)
    real = shutil.which("git", path=os.pathsep.join(p for p in path.split(os.pathsep) if Path(p) != folder))
    if real is None:
        raise RuntimeError(NO_GIT)
    shim = folder / "git"
    shim.write_text(SHIM.format(git=real, offset=Path(state) / OFFSET_FILE), encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return os.pathsep.join([str(folder), path])
