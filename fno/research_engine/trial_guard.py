"""What must hold before a period of an experiment is run (stories B3 and B4). Checked before any data is read.

- Every trial of the run (policies and controls) is registered in a committed ledger (B4's `require_committed`).
- The decisive period (experiment 1: the challenge, protocol section 8) also needs B4's full check (frozen protocol
  commit, protocol unchanged since) and a "frozen at commit <hash>" line in the protocol file whose commit exists and
  precedes the run (B3 criterion 6), and the protocol at that commit equals today's protocol without that line (the
  rules cannot change between the named commit and the commit that adds the line).
- An already looked-at period (discovery) is reported, never judged, so it needs the registration only.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Sequence

from .ledger import Ledger

FROZEN_LINE = re.compile(r"frozen at commit\s+`?([0-9a-f]{7,40})\b", re.IGNORECASE)


class ProtocolNotFrozen(RuntimeError):
    """The decisive period may not run: the protocol carries no valid "frozen at commit" line."""


def without_frozen_line(protocol_text: str) -> str:
    return "".join(line for line in protocol_text.splitlines(keepends=True) if not FROZEN_LINE.search(line))


def frozen_commit(protocol_text: str) -> str | None:
    """The commit named by the protocol's "frozen at commit <hash>" line, if it has one."""
    found = FROZEN_LINE.search(protocol_text)
    return found.group(1) if found else None


class TrialGuard(ABC):
    @abstractmethod
    def check(self, trial_ids: Sequence[str], protocol_path: str, decisive: bool) -> None:
        """Raises (NotRegistered or ProtocolNotFrozen) when the run may not start."""


class LedgerTrialGuard(TrialGuard):
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def check(self, trial_ids: Sequence[str], protocol_path: str, decisive: bool) -> None:
        for trial_id in trial_ids:
            if decisive:
                self.ledger.require_registered(trial_id)
            else:
                self.ledger.require_committed(trial_id)
        if decisive:
            self._require_frozen(protocol_path)

    def _require_frozen(self, protocol_path: str) -> None:
        path = self.ledger.root / protocol_path
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        commit, git = frozen_commit(text), self.ledger.git
        if commit is None:
            raise ProtocolNotFrozen(f"{protocol_path} has no 'frozen at commit <hash>' line")
        if not git.commit_exists(commit) or not git.is_ancestor(commit, git.head()):
            raise ProtocolNotFrozen(
                f"{protocol_path}: frozen commit {commit} does not exist or does not precede the run"
            )
        if git.committed_text(protocol_path, commit) != without_frozen_line(text):
            raise ProtocolNotFrozen(f"{protocol_path} changed after its frozen commit {commit}")
