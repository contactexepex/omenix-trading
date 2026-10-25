"""The daily run's git side (story E3): `GitCommitter` commits and pushes the run's public files (run logs, the daily
totals, pack hashes). Since story E2c the paper accounts live in Drive (`fno.desk.private_files`), so no account write
touches git any more. Every commit passes the raw-quote guard and runs the repository's hooks (the public-record scan,
O5): never `--no-verify`."""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path

from ..config import ROOT
from ..constants import PUBLISH_BRANCH
from ..storage.wiring import QUOTES_FOLDER
from .commit_guard import RawQuoteCommitRefused, RawQuoteGuard
from .daily_ports import AccountWriteRefused, CommitFailed, Committer, OwnCommit
from .git_limit import GIT_CALL_LIMIT_SECONDS, LimitedRun
from .own_commits import OwnUnpushed

PUSH_ATTEMPTS = 3
STOPPED = "git {what} ran past {seconds:.0f} s and was stopped with its hooks{removed}"
REMOVED = "; its own lock files removed: {names}"
HELD_LOCK = re.compile(r"'([^']+\.lock)': File exists")
HAND_FIX = " (no git running? remove {lock} by hand, then rerun)"


class GitError(AccountWriteRefused):
    """A git step failed; the message names it. For the daily run, any git failure refuses that account write."""


class PushRejected(GitError):
    """Every push attempt was rejected: the commit stays local and unpushed."""


class GitCallStopped(GitError):
    """A git call ran past its hard limit and was stopped (story O2)."""


class PushNotConfirmed(PushRejected):
    """A push stopped at its limit: it may have reached origin, so the run treats its commit as unpushed."""


STRAY = "the checkout holds {count} unpushed commit(s) the run did not make ({what}); never pushed: resolve by hand"


class Git:
    def __init__(self, root: Path, run=None, guard: RawQuoteGuard | None = None, limit_seconds: float | None = None,
                 target: str = PUBLISH_BRANCH):  # fmt: skip
        """`limit_seconds`: every call's hard limit, `GIT_CALL_LIMIT_SECONDS` unless given (read when built).
        `target`: the one branch every fetch, compare and push uses, never the checkout's own (a scheduled session's
        branch is not on origin)."""
        self.root, self.run, self.target = Path(root), run or LimitedRun(), target
        self.limit_seconds = GIT_CALL_LIMIT_SECONDS if limit_seconds is None else limit_seconds
        self.guard = guard or RawQuoteGuard(self.root, self.root / QUOTES_FOLDER.relative_to(ROOT))

    def __call__(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        done = self._run(["git", *args], text=True)
        if check and done.returncode != 0:
            said = (done.stderr or done.stdout).strip()
            held = HELD_LOCK.search(said)
            hand_fix = HAND_FIX.format(lock=held.group(1)) if held else ""
            raise GitError(f"git {' '.join(args[:2])} failed: {said[-300:]}{hand_fix}")
        return done

    def _run(self, command: list[str], text: bool) -> subprocess.CompletedProcess:
        """Every git call of the run, under the one hard limit (story O2)."""
        try:
            return self.run(command, cwd=self.root, capture_output=True, text=text, timeout=self.limit_seconds)
        except subprocess.TimeoutExpired as expired:
            removed = getattr(expired, "removed", [])
            names = REMOVED.format(names=", ".join(removed)) if removed else ""
            what = " ".join(command[1:3])
            raise GitCallStopped(STOPPED.format(what=what, seconds=self.limit_seconds, removed=names)) from None

    def unshallow(self) -> bool:
        """Fetches the whole history when the checkout is shallow (story O1: commit times are dates); False when it
        was whole already. `GitError` when the fetch fails or runs past the hard limit every call has, so a hung fetch
        never holds the day."""
        if self("rev-parse", "--is-shallow-repository").stdout.strip() != "true":
            return False
        self("fetch", "-q", "--unshallow", "origin", self.target)
        return True

    def commit_paths(self, paths: Sequence[Path], message: str) -> bool:
        """Adds and commits these paths, and only these (a pathspec commit: a file staged earlier by anything else is
        never swept in, judge 169 addendum 1); False when nothing changed in them. The raw-quote guard still checks
        every staged file after the add (a folder expands there, and another writer's staged file is seen too); on a
        refusal this add is undone (another writer's staged files are left as they were, so the next commit refuses
        too) and nothing is committed."""
        self.guard.check(paths)
        added = [self.relative(p) for p in paths]
        self("add", "--", *added)
        try:
            self.guard.check(self.staged())
        except RawQuoteCommitRefused:
            self("reset", "-q", "--", *added, check=False)
            raise
        if self("diff", "--cached", "--quiet", "--", *added, check=False).returncode == 0:
            return False
        self("commit", "-q", "-m", message, "--", *added)
        return True

    def changed(self, pathspecs: Sequence[str]) -> list[Path]:
        """The files under these pathspecs that a commit would add or change: modified or new, git-ignored ones left
        out (a Groww raw quote file is ignored, A4b), so a part's commit is exactly its own files (story O1)."""
        names = self("ls-files", "-z", "--modified", "--others", "--exclude-standard", "--", *pathspecs).stdout
        return sorted({self.root / name for name in names.split("\0") if name})

    def staged(self) -> list[Path]:
        """Every path in the index that differs from HEAD (a staged deletion too): what the next commit would carry."""
        names = self("diff", "--cached", "--name-only", "-z").stdout.split("\0")
        return [self.root / name for name in names if name]

    def push(self) -> bool:
        try:
            return self("push", "-q", "origin", f"HEAD:{self.target}", check=False).returncode == 0
        except GitCallStopped as stopped:
            raise PushNotConfirmed(f"push not confirmed: {stopped}") from None

    def relative(self, path: Path) -> str:
        return Path(path).resolve().relative_to(self.root.resolve()).as_posix()

    def unpushed(self, *options: str) -> list[str]:
        """Commits on HEAD that origin does not have (after a fetch): what a push would publish. The one rule both the
        account writes and the run's commits start from (decision 51)."""
        self("fetch", "-q", "origin", self.target)
        return self.ahead_of(f"origin/{self.target}", *options)

    def unpushed_files(self) -> list[Path]:
        """Every file a push would change on origin (a deletion too), whoever made the commits."""
        names = self("diff", "--name-only", "-z", f"origin/{self.target}", "HEAD").stdout.split("\0")
        return [self.root / name for name in names if name]

    def subject(self, commit: str) -> str:
        return self("show", "-s", "--format=%s", commit).stdout.strip()

    def content_sha256(self, commit: str, name: str) -> str | None:
        """The SHA-256 of `name` as `commit` holds it; None when the commit holds no such file (deleted)."""
        data = self.show(commit, name)
        return hashlib.sha256(data).hexdigest() if data is not None else None

    def show(self, commit: str, name: str) -> bytes | None:
        """`name`'s bytes as `commit` holds it; None when it holds no such file."""
        done = self._run(["git", "show", f"{commit}:{name}"], text=False)
        return done.stdout if done.returncode == 0 else None

    def files_of(self, commit: str) -> set[str]:
        names = self("diff-tree", "--no-commit-id", "--name-only", "-r", "-z", commit).stdout.split("\0")
        return {name for name in names if name}

    def ahead_of(self, commit: str, *options: str) -> list[str]:
        return self("rev-list", *options, f"{commit}..HEAD").stdout.split()


class GitCommitter(Committer):
    """Every commit passes `RawQuoteGuard` (story E2b): first on the given paths, before git runs (not even the pull),
    then on everything staged (`Git.commit_paths`), and before every push on every file the push would change. An
    unpushed commit the run did not make is refused before the pull (decision 51): the only one allowed is the run's
    own `own_unpushed` commit: its message, and only the pending marker's files with their recorded content. With
    `own` (story O1, gap G4), every commit this committer made and could not push yet is accepted the same way, so one
    part's failed push never stops the desk's next commit. Any refusal or git failure is raised as `CommitFailed`."""

    def __init__(self, git: Git, own: OwnUnpushed | None = None):
        self.git, self.own = git, own or OwnUnpushed()

    def commit(self, paths: Sequence[Path], message: str, own_unpushed: OwnCommit | None = None) -> str:
        try:
            return self._commit(paths, message, own_unpushed)
        except (RawQuoteCommitRefused, GitError) as failure:
            raise CommitFailed(str(failure), unpushed=isinstance(failure, PushRejected)) from failure

    def _commit(self, paths: Sequence[Path], message: str, own_unpushed: OwnCommit | None) -> str:
        self.git.guard.check(paths)
        self._refuse_stray(own_unpushed)
        branch = self.git.target
        self.git("pull", "-q", "--no-rebase", "--no-edit", "origin", branch)
        if self.git.commit_paths(paths, message):
            self.own.remember(self._recorded("HEAD"))  # until a push carries it (G4)
        if self.git.ahead_of(f"origin/{branch}"):  # this commit, or one left unpushed
            self._push(message, branch)
        self.own.pushed()  # origin holds every commit this committer made
        return self.git("rev-parse", "HEAD").stdout.strip()

    def _push(self, message: str, branch: str) -> None:
        for _ in range(PUSH_ATTEMPTS):
            self.git.guard.check(self.git.unpushed_files())
            if self.git.push():
                return
            self.git("pull", "-q", "--no-rebase", "--no-edit", "origin", branch)
        raise PushRejected(f"push of '{message}' rejected {PUSH_ATTEMPTS} times; the commit stays local, unpushed")

    def _refuse_stray(self, own: OwnCommit | None) -> None:
        """A merge made by a retry's pull is not a stray: what it brings in is checked commit by commit here, and every
        file it changes on origin by the guard before the push."""
        allowed = [*([own] if own else []), *self.own.commits]
        stray = [c for c in self.git.unpushed("--no-merges") if not any(self._own(c, mine) for mine in allowed)]
        if stray:
            what = "; ".join(f"'{self.git.subject(c)}': {', '.join(sorted(self.git.files_of(c)))}" for c in stray)
            raise GitError(STRAY.format(count=len(stray), what=what))

    def _recorded(self, commit: str) -> OwnCommit:
        return OwnCommit(
            self.git.subject(commit), {f: self.git.content_sha256(commit, f) for f in self.git.files_of(commit)}
        )

    def _own(self, commit: str, own: OwnCommit) -> bool:
        """Exact: the same message, and each file the commit touches as the marker recorded it (judge 118 add. 7)."""
        if self.git.subject(commit) != own.message:
            return False
        files = self.git.files_of(commit)
        return files <= set(own.files) and all(self.git.content_sha256(commit, f) == own.files[f] for f in files)
