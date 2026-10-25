"""Story O2: every git call of the daily run has one hard limit. A call past it is stopped with its whole process group
(git and the hooks it started, as `fno/daily/processes.py` stops a command), and the lock files that call created are
removed, so one hung pull, commit or push can neither hold the run's one thread (and the 15:15 exits) nor leave
`.git/index.lock` behind to fail every later call (judge 204 addendum 2).

A lock is removed only when the stopped call created it (absent before the call) and no other git process is alive
(judge 204 addendum 3 note 1: a child command of the run that runs git would hold its own locks). A lock that was
already there is never touched: git's own "File exists" error fails the call at once, and the error names the lock."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path

GIT_CALL_LIMIT_SECONDS = 120.0  # the whole-history fetch's limit (judge 178 add. 10: a fresh full fetch took 6.7 s)
LOCK_SUFFIX = ".lock"
SKIPPED_FOLDERS = frozenset({"objects", "lfs"})  # never locks git takes for a commit, pull or push; large
PROC = Path("/proc")
GROUP_GONE_SECONDS = 5.0  # SIGKILL ends each process when the kernel reaches it: how long to wait for the last one


class GitLocks:
    """The lock files in one checkout's `.git` folder."""

    def __init__(self, root: Path, proc: Path = PROC):
        self.git_dir, self.proc = Path(root) / ".git", proc

    def present(self) -> set[Path]:
        found = set()
        for folder, subfolders, files in os.walk(self.git_dir):
            subfolders[:] = [name for name in subfolders if name not in SKIPPED_FOLDERS]
            found.update(Path(folder) / name for name in files if name.endswith(LOCK_SUFFIX))
        return found

    def remove_new(self, before: set[Path]) -> list[str]:
        """Removes the locks that appeared since `before`, unless a git process is still alive; their names."""
        new = sorted(self.present() - before)
        if not new or self._git_alive():
            return []
        for lock in new:
            with contextlib.suppress(FileNotFoundError):
                lock.unlink()
        return [lock.relative_to(self.git_dir.parent).as_posix() for lock in new]

    def _git_alive(self) -> bool:
        """True when any git process runs (`git`, `git-remote-https`, ...), or when that cannot be seen (no /proc): then
        nothing is removed."""
        if not self.proc.is_dir():
            return True
        for entry in self.proc.iterdir():
            with contextlib.suppress(OSError):
                if entry.name.isdigit() and (entry / "comm").read_text().startswith("git"):
                    return True
        return False


class LimitedRun:
    """A `subprocess.run` for git: the call runs in its own process group and ends by `timeout` at the latest. Past
    it, the group is killed and reaped, the call's own new locks are removed, and `subprocess.TimeoutExpired` is raised
    with `removed` (the lock names) set on it."""

    def __init__(self, locks: Callable[[Path], GitLocks] = GitLocks,
                 started: Callable[[Sequence[str]], None] = lambda command: None, proc: Path = PROC):  # fmt: skip
        """`started`: called once the call runs, before its limit counts. The run passes nothing; a test waits there
        until a hook has been reached, so its limit never races git's own start on a loaded machine."""
        self.locks, self.started, self.proc = locks, started, proc

    def __call__(self, command: Sequence[str], *, cwd: Path, timeout: float, capture_output: bool = True,
                 text: bool = False) -> subprocess.CompletedProcess:  # fmt: skip
        locks = self.locks(cwd)
        before = locks.present()
        pipe = subprocess.PIPE if capture_output else None
        with subprocess.Popen(command, cwd=cwd, stdout=pipe, stderr=pipe, text=text, start_new_session=True) as popen:
            self.started(command)
            try:
                out, err = popen.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(popen.pid, signal.SIGKILL)
                popen.communicate()
                self._until_gone(popen.pid)
                expired = subprocess.TimeoutExpired(list(command), timeout)
                expired.removed = locks.remove_new(before)
                raise expired from None
        return subprocess.CompletedProcess(list(command), popen.returncode, out, err)

    def _until_gone(self, group: int) -> None:
        """Returns once no process of the stopped group still runs, so "stopped with its hooks" is true when said: a
        hook is git's grandchild, which `communicate` does not wait for (A4 builder, 22 Oct). A zombie counts as gone:
        it holds nothing and waits only for its new parent, which may never reap it in a container."""
        deadline = time.monotonic() + GROUP_GONE_SECONDS
        while running_in_group(group, self.proc) and time.monotonic() < deadline:
            time.sleep(0.01)


def running_in_group(group: int, proc: Path = PROC) -> bool:
    """True while a live process (not a zombie) of the process group runs; False when /proc cannot tell."""
    if not proc.is_dir():
        return False
    for entry in proc.iterdir():
        with contextlib.suppress(OSError, IndexError, ValueError):
            if entry.name.isdigit():
                state, _parent, process_group = (entry / "stat").read_text().rsplit(")", 1)[1].split()[:3]
                if int(process_group) == group and state != "Z":
                    return True
    return False
