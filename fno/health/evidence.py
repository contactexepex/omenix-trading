"""What the checks read: the repository's files, and when GitHub received them. The push time is F1's `PushReceipts`
(GitHub's activity log), found for the commit that first added the file or the session's row; a commit's own date is
never used. Searches start the day before the session, so they stay inside the window."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from ..ai.history import RepoHistory
from ..ai.receipts import PushReceipts, ReceiptNotFound, ReceiptOutsideLog, ReceiptUnknown
from .model import EvidenceNotCommitted, EvidenceNotPushed, EvidenceOutsideLog, EvidenceUnknown

ANSWERS = {ReceiptNotFound: EvidenceNotPushed, ReceiptOutsideLog: EvidenceOutsideLog}


class HealthHistory(RepoHistory):
    def first_commit_adding_text(self, path: str, text: str, since: date) -> str | None:
        """The earliest commit since `since` whose change to `path` added `text` (git's pickaxe)."""
        found = self._out("log", "--format=%H", "--reverse", f"--since={since.isoformat()}", "-S", text, "--", path)
        commits = found.split()
        return commits[0] if commits else None


class Evidence:
    def __init__(self, root: Path, history: HealthHistory, receipts: PushReceipts):
        self.root, self.history, self.receipts = Path(root), history, receipts

    def text(self, path: str) -> str | None:
        file = self.root / path
        if not file.is_file():
            return None
        try:
            return file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise EvidenceUnknown(f"{path} unreadable ({type(error).__name__})") from None

    def json(self, path: str) -> dict | None:
        text = self.text(path)
        if text is None:
            return None
        try:
            return json.loads(text)
        except ValueError:
            raise EvidenceUnknown(f"{path} is not valid JSON") from None

    def file_pushed_at(self, path: str) -> datetime:
        return self._received(self.history.first_commit_adding(path), path)

    def row_pushed_at(self, path: str, text: str, session: date) -> datetime:
        return self._received(self.history.first_commit_adding_text(path, text, session - timedelta(days=1)), path)

    def _received(self, commit: str | None, path: str) -> datetime:
        if not commit:
            raise EvidenceNotCommitted(f"no commit adding it to {Path(path).name}")
        try:
            return self.receipts.received_at(commit)
        except ReceiptUnknown as unknown:
            kind = ANSWERS.get(type(unknown), EvidenceUnknown)  # a failed read stays a plain unknown
            raise kind(f"push time unknown: {unknown}") from None
