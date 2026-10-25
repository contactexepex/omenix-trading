"""What a practice run depended on, for its id (story MS-SIM-e2; orchestrator, 23 Oct): the committed code and the data
the run read that moves from day to day. The archived NSE files are write-once and named by the window, so the window
identifies them; the recorded captures grow every day, so the spread model learned from them is hashed, together with
the margin factor's label. New code or new captures make a new run id, so an archived run is never touched."""

import hashlib
import subprocess
from pathlib import Path

from ..spreads.model import SpreadModel

CODE_PATHS = (
    "fno",
    "tools",
    "config.yaml",
    "requirements.txt",
)  # what a run's behaviour rests on: code, settings, libraries
DIRTY = (
    "the code is not committed ({paths}): a run id names the committed code, so commit first or run without --archive"
)
NO_CODE = "cannot name the code: {reason}"
IDENTITY_CHARS = 12


class CodeNotCommitted(Exception):
    """The checkout differs from the committed code the run id would name, or the code cannot be named."""


def code_identity(repository: Path, run=subprocess.run) -> str:
    """The code by content: a digest of the tree ids of the code paths in HEAD. Not a commit id: each receipt commit
    and each pull of other sessions' data moves HEAD (found by the first real archived run, SIM-e3), and a history
    search for the last code commit gives another answer in a shallow clone than in a full one. Tree ids need no
    history, so the same code gives the same id in any clone, on any branch, before and after a receipt commit. The
    installed library versions are not in it: `requirements.txt` holds ranges, so it names the requirement text."""

    def git(*args: str) -> list[str]:
        done = run(["git", *args], cwd=repository, capture_output=True, text=True)
        if done.returncode != 0:
            raise CodeNotCommitted(NO_CODE.format(reason=(done.stderr or "git failed").strip()))
        return done.stdout.splitlines()  # not stripped: a status line starts with a space

    changed = git("status", "--porcelain", "--untracked-files=all", "--", *CODE_PATHS)
    if changed:
        raise CodeNotCommitted(DIRTY.format(paths=", ".join(line[3:] for line in changed[:3])))
    trees = [f"{path}={git('rev-parse', f'HEAD:{path}')[0]}" for path in CODE_PATHS]
    return hashlib.sha256("\n".join(trees).encode()).hexdigest()[:IDENTITY_CHARS]


def inputs_digest(spreads: SpreadModel, margin_label: str) -> str:
    """The spread model's every (bucket, session, relative half-spread) and the margin factor's label, order-free."""
    rows = sorted(f"{bucket}|{day}|{value!r}" for bucket, days in spreads.by_session.items()
                  for day, value in days.items())  # fmt: skip
    return hashlib.sha256("\n".join([*rows, margin_label]).encode()).hexdigest()
