"""Publishing a record (story DR1; judge 543 SF1): a record counts only once origin's main holds it with the same
bytes. A refused push leaves a local commit that the committer will never push again (it sees nothing pending), so
the publisher asks origin itself: the same bytes there are "pushed"; other bytes are a conflict (another certifier
published first, and first push wins); nothing there means pull and push once more, else "not pushed" with the
reason. Never `--no-verify`: the commit is the committer's, with the record scan."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..storage.manifest_commit import TARGET_BRANCH, GitManifestRecorder

PUSHED, NOT_PUSHED, CONFLICT = "pushed", "not pushed", "conflict"
NOT_ON_MAIN = "not on origin/{branch} after the push ({why})"


@dataclass(frozen=True)
class Published:
    state: str
    detail: str = ""
    held: bytes | None = None  # a conflict: the record origin's main holds


class RecordPublisher(ABC):
    @abstractmethod
    def publish(self, file: Path, what: str) -> Published: ...


class GitRecordPublisher(RecordPublisher):
    def __init__(self, repository: Path, committer: GitManifestRecorder, run=subprocess.run):
        self.repository, self.committer, self.run = Path(repository), committer, run

    def publish(self, file: Path, what: str) -> Published:
        outcome = self.committer.commit(what)
        name, mine = file.relative_to(self.repository).as_posix(), file.read_bytes()
        why = outcome
        for retry in (True, False):
            fetched = self._git("fetch", "-q", "origin", TARGET_BRANCH)
            if fetched.returncode != 0:
                return Published(NOT_PUSHED, f"fetch failed: {_first_line(fetched)}")
            held = self._git("show", f"origin/{TARGET_BRANCH}:{name}", text=False)
            if held.returncode == 0:
                return Published(PUSHED) if held.stdout == mine else Published(CONFLICT, held=held.stdout)
            if retry:
                why = self._push_again() or why
        return Published(NOT_PUSHED, NOT_ON_MAIN.format(branch=TARGET_BRANCH, why=why))

    def _push_again(self) -> str:
        """Pulls main and pushes HEAD once; returns why it failed ("" when git accepted it)."""
        pulled = self.committer.pull()
        if pulled.returncode != 0:
            self.committer.abort_merge()
            return f"pull failed: {_first_line(pulled)}"
        pushed = self._git("push", "-q", "origin", f"HEAD:{TARGET_BRANCH}")
        return "" if pushed.returncode == 0 else f"push refused: {_first_line(pushed)}"

    def _git(self, *args: str, text: bool = True) -> subprocess.CompletedProcess:
        return self.run(["git", "-C", str(self.repository), *args], capture_output=True, text=text, check=False)


def _first_line(result: subprocess.CompletedProcess) -> str:
    raw = result.stderr or result.stdout or ""
    lines = (raw.decode(errors="replace") if isinstance(raw, bytes) else raw).strip().splitlines()
    return lines[0] if lines else f"exit code {result.returncode}"
