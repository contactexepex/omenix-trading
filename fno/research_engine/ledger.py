"""The research ledger guard (story B4): no trial runs unless it was registered first, proved by git history.

`research/ledger.csv` is the machine record (one row per trial); `research/LEDGER.md` is the readable history. A trial
may run only if:
1. the ledger file equals the committed HEAD version (no staged or unstaged edits), and the commit that first added
   the trial's row is an ancestor of the commit being run (registration is in history and cannot be back-dated);
2. it names a frozen protocol (commit and file) that is an ancestor of the commit being run;
3. the protocol file is unchanged since that frozen commit.
Trials 1-31 were recorded while or after being run: they are `retrospective` and never presented as pre-registered.
"""

from __future__ import annotations

import csv
import io
import os
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..models import today_local
from ..numbering.blocks import TrialClaims

LEDGER_FILE = "research/ledger.csv"
COLUMNS = (
    "trial_id", "experiment", "description", "kind", "hypothesis", "registered_on", "protocol_path",
    "protocol_commit", "first_run_on", "run_commit",
)  # fmt: skip
KINDS = ("retrospective", "prospective", "control")


class NotRegistered(RuntimeError):
    """The trial may not run: it is missing, not committed, or its protocol is not frozen and unchanged."""


# git's own "not there" answers (measured 22 Oct 2026 on git 2.43.0: all exit 128), each true only for its own kind
# of question; any other non-zero exit is a failure and raises. A file's: not at that revision (`show`; a revision git
# cannot resolve is a wrong question and raises, D5 builder). An object's: no such commit (the yes/no questions). A
# history's: no commits yet (`log` in a new repository).
FILE_NOT_THERE = ("does not exist in", "exists on disk, but not in")
OBJECT_NOT_THERE = ("invalid object name", "Not a valid object name", "Not a valid commit name", "bad object")
NO_HISTORY_YET = ("does not have any commits yet",)
FAILED = "git {command} failed (exit {code}): {why}"


class GitFailed(RuntimeError):
    """A git command failed for a reason other than "not there" (a broken repository, no memory, a refused pull).
    Raised, never read as an empty answer: an empty answer would become a wrong record (a real submission read as
    missing)."""


@dataclass(frozen=True)
class Git:
    """The few git questions the guard asks, against one repository folder. Every question either gets git's real
    answer or raises `GitFailed`; a failed command is never read as "nothing found"."""

    root: Path

    def _run(self, *args: str, text: bool = True) -> subprocess.CompletedProcess:
        # git's "not there" answers are matched by their English text: a translated git must not turn them into errors
        env = {**os.environ, "LC_ALL": "C"}
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=text, env=env)

    def _out(self, *args: str) -> str:
        """The command's output: empty for a history with no commits yet, GitFailed on any other non-zero exit."""
        done = self._found(*args, not_there=NO_HISTORY_YET)
        return "" if done is None else done.stdout

    def _found(self, *args: str, not_there: tuple[str, ...], text: bool = True) -> subprocess.CompletedProcess | None:
        """The finished command, or None when git gives one of the `not_there` answers."""
        done = self._run(*args, text=text)
        return None if _says(done, not_there) else self._checked(done, args)

    def _yes(self, *args: str) -> bool:
        """A question git answers by its exit code: 0 yes, 1 no (or no such object); anything else raises."""
        done = self._run(*args)
        return done.returncode == 0 or (done.returncode != 1 and not _says(done, OBJECT_NOT_THERE)
                                        and self._checked(done, args))  # fmt: skip

    @staticmethod
    def _checked(done: subprocess.CompletedProcess, args: tuple[str, ...]) -> subprocess.CompletedProcess:
        if done.returncode != 0:
            why = _stderr(done).strip()[-300:] or "no message"
            raise GitFailed(FAILED.format(command=args[0], code=done.returncode, why=why))
        return done

    def head(self) -> str:
        return self._out("rev-parse", "HEAD").strip()

    def is_ancestor(self, older: str, newer: str) -> bool:
        return bool(older) and self._yes("merge-base", "--is-ancestor", older, newer)

    def first_commit_containing(self, text: str, path: str) -> str | None:
        """The earliest commit whose change to `path` added `text` (git's pickaxe search)."""
        found = self._out("log", "--format=%H", "--reverse", "-S", text, "--", path).split()
        return found[0] if found else None

    def committed_text(self, path: str, commit: str = "HEAD") -> str | None:
        """The file as committed at `commit` (None if not committed there). git gives the same answer for a full SHA
        that is no commit at all, so a caller that needs the commit to exist asks `commit_exists` first."""
        done = self._found("show", f"{commit}:{path}", not_there=FILE_NOT_THERE)
        return None if done is None else done.stdout

    def commits_touching(self, path: str) -> list[str]:
        """Every commit that changed `path`, oldest first (story D5: the strategy registry's append-only check)."""
        return self._out("log", "--format=%H", "--reverse", "--", path).split()

    def changes_with_parents(self, path: str, revision: str = "HEAD") -> list[tuple[str, tuple[str, ...]]]:
        """Every commit in `revision`'s history that changed `path` against any of its parents, merges included, each
        with its real parents (story D5: a merge of parallel registrations is two appends, not an edit)."""
        lines = self._out("log", "--format=%H %P", "--full-history", revision, "--", path).splitlines()
        return [(line.split()[0], tuple(line.split()[1:])) for line in lines if line.strip()]

    def is_shallow(self) -> bool:
        """A shallow clone lacks the older history, so a history check would pass on what it cannot see."""
        return self._out("rev-parse", "--is-shallow-repository").strip() != "false"

    def deepen_since(self, since: date, branch: str) -> None:
        """Fetches `branch`'s history back to `since` into a shallow clone, so a "first commit adding the file" is the
        real one, not the clone's boundary commit; a refused fetch raises."""
        self._out("fetch", "--quiet", f"--shallow-since={since.isoformat()}", "origin", branch)

    def commit_exists(self, commit: str) -> bool:
        return bool(commit) and self._yes("cat-file", "-e", f"{commit}^{{commit}}")

    def is_clean(self, path: str) -> bool:
        """No local change to `path`, tracked or untracked (`git diff` alone misses a file never committed)."""
        return not self._out("status", "--porcelain", "--", path).strip()

    def unchanged_since(self, commit: str, path: str) -> bool:
        tracked = self._yes("diff", "--quiet", commit, "HEAD", "--", path)
        untouched = self._yes("diff", "--quiet", "HEAD", "--", path)
        return tracked and untouched


def _stderr(done: subprocess.CompletedProcess) -> str:
    err = done.stderr or ""
    return err.decode("utf-8", "replace") if isinstance(err, bytes) else err


def _says(done: subprocess.CompletedProcess, answers: tuple[str, ...]) -> bool:
    return done.returncode != 0 and any(answer in _stderr(done) for answer in answers)


def read_ledger(text: str) -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(text)))
    for row in rows:
        if tuple(row) != COLUMNS:
            raise ValueError(f"ledger columns must be {COLUMNS}")
        if row["kind"] not in KINDS or row["hypothesis"] not in ("yes", "no"):
            raise ValueError(f"trial {row['trial_id']}: bad kind or hypothesis flag")
    ids = [r["trial_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate trial ids in the ledger")
    return rows


def write_ledger(rows: list[dict]) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


class TrialNotClaimed(ValueError):
    """The trial id is not in a block claimed for its experiment (story O12e): claim one on `main` first."""


class Ledger:
    def __init__(self, root: Path, git: Git | None = None, claims: TrialClaims | None = None):
        self.root, self.git = Path(root), git or Git(Path(root))
        self.file = self.root / LEDGER_FILE
        self.claims = claims or TrialClaims(self.git.committed_text, self.git.is_clean)

    def rows(self) -> list[dict]:
        return read_ledger(self.file.read_text()) if self.file.is_file() else []

    def register(self, trial_id: str, experiment: str, description: str, kind: str, hypothesis: bool,
                 protocol_path: str = "", today: date | None = None) -> None:  # fmt: skip
        """Adds a row (commit it before the trial runs). A whole-number id must sit in a block claimed for this
        experiment (story O12e), so two branches never take the same ids."""
        rows = self.rows()
        if any(r["trial_id"] == trial_id for r in rows):
            raise ValueError(f"trial {trial_id} is already registered")
        unclaimed = self.claims.problem(trial_id, experiment)
        if unclaimed:
            raise TrialNotClaimed(unclaimed)
        row = dict.fromkeys(COLUMNS, "")
        row.update(trial_id=trial_id, experiment=experiment, description=description, kind=kind,
                   hypothesis="yes" if hypothesis else "no", registered_on=(today or today_local()).isoformat(),
                   protocol_path=protocol_path)  # fmt: skip
        read_ledger(write_ledger([*rows, row]))  # validates
        self.file.write_text(write_ledger([*rows, row]))

    def require_committed(self, trial_id: str) -> dict:
        """The trial's row if its registration is committed history (no protocol check): enough to run an already
        looked-at period, never the one that decides. NotRegistered with the reason otherwise."""
        row = next((r for r in self.rows() if r["trial_id"] == trial_id), None)
        if row is None:
            raise NotRegistered(f"trial {trial_id} is not registered: it is not in {LEDGER_FILE}")
        unclaimed = self.claims.problem(trial_id, row["experiment"])  # a row typed by hand never passed `register`
        if unclaimed:
            raise NotRegistered(unclaimed)
        committed = self.git.committed_text(LEDGER_FILE)
        if committed is None or not self.git.unchanged_since("HEAD", LEDGER_FILE):
            raise NotRegistered("the ledger has uncommitted changes: commit it so the run uses exactly what is in git")
        if row not in read_ledger(committed):
            raise NotRegistered(f"trial {trial_id}: its row differs from the committed ledger")
        registered = self.git.first_commit_containing(f"\n{trial_id},", LEDGER_FILE)
        if not registered or not self.git.is_ancestor(registered, self.git.head()):
            raise NotRegistered(f"trial {trial_id} is not in a committed ledger (commit the registration first)")
        return row

    def require_registered(self, trial_id: str) -> dict:
        """The trial's row if it may run now; NotRegistered with the reason otherwise. Call before reading any data."""
        row = self.require_committed(trial_id)
        if not row["protocol_commit"] or not row["protocol_path"]:
            raise NotRegistered(f"trial {trial_id} has no frozen protocol commit")
        if not self.git.is_ancestor(row["protocol_commit"], self.git.head()):
            raise NotRegistered(f"trial {trial_id}: protocol commit {row['protocol_commit'][:10]} is not in history")
        if not self.git.unchanged_since(row["protocol_commit"], row["protocol_path"]):
            raise NotRegistered(f"trial {trial_id}: {row['protocol_path']} changed after it was frozen")
        return row

    def mark_run(self, trial_id: str, commit: str, today: date | None = None) -> None:
        """Records the first run once (date and the commit it ran at, read by the caller before it wrote anything);
        later runs never change it."""
        rows = self.rows()
        for row in rows:
            if row["trial_id"] == trial_id and not row["first_run_on"]:
                row["first_run_on"], row["run_commit"] = (today or today_local()).isoformat(), commit
        self.file.write_text(write_ledger(rows))

    def count(self, experiment: str) -> dict[str, int]:
        rows = [r for r in self.rows() if r["experiment"] == experiment]
        return {"registered_rows": len(rows), "hypotheses": sum(r["hypothesis"] == "yes" for r in rows)}
