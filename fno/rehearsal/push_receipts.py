"""When a rehearsal's commit reached its origin, by the replay clock (story REH1b), behind F1's `PushReceipts`. A
rehearsal pushes to its local bare origin, which GitHub's activity log never sees; that origin's `post-receive` hook
logs each push with the replay time, and a commit's receipt is the first logged push that brings it, as
`GitHubActivityReceipts` reads GitHub's log. Unclear answers raise `ReceiptUnknown`, failing closed as ever."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ..ai.receipts import PushReceipts, ReceiptNotFound
from .clock import OFFSET_FILE

PUSH_LOG = "pushes.log"
HOOK = """#!/bin/sh
# Story REH1b: each push to this rehearsal's origin, logged with the replay time (for its push receipts)
offset=$(cat '{offset}')
stamp=$(awk -v t="$(date +%s.%N)" -v o="$offset" 'BEGIN {{ printf "%d", t + o }}')
while read old new ref; do
  [ "$ref" = "refs/heads/main" ] && echo "$stamp $old $new" >> '{log}'
done
exit 0
"""
NOT_PUSHED = "no push of {commit} to the rehearsal's origin (its push log: {log})"


def post_receive_hook(state: Path) -> str:
    return HOOK.format(offset=Path(state) / OFFSET_FILE, log=Path(state) / PUSH_LOG)


class LocalPushReceipts(PushReceipts):
    def __init__(self, log: Path, history):
        self.log, self.history = Path(log), history

    def received_at(self, commit: str) -> datetime:
        lines = self.log.read_text(encoding="utf-8").splitlines() if self.log.is_file() else []
        for line in lines:
            stamp, old, new = line.split()
            if self.history.is_ancestor(commit, new) and not self._held(commit, old):
                return datetime.fromtimestamp(int(stamp), UTC)
        raise ReceiptNotFound(NOT_PUSHED.format(commit=commit[:10], log=self.log))

    def _held(self, commit: str, old: str) -> bool:
        return set(old) != {"0"} and self.history.is_ancestor(commit, old)
