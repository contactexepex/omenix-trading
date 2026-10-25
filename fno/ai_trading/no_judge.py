"""The judge until F4's code lands (story F1t criterion 16; F4 design 4, judge 628 m1): every verdict is `unavailable`,
"judge not built (F4)". It still writes the day's verdict file once, with F4's fields where they apply, so a Book 2
day judged this way has its record: Book 2 is then `judge_failed` every day (fail closed, never a trade), and Book
3's verdicts never block."""

from __future__ import annotations

import json
from pathlib import Path

from ..constants import BOOK2_HYBRID
from ..desk.pack_items import canonical_json, sha256_hex
from .paths import judge_path
from .ports import JudgeCase, Judged, JudgeStep, JudgeVerdict

UNAVAILABLE, NOT_BUILT = "unavailable", "judge not built (F4)"
JUDGE_ID = "none:not-built"


class VerdictRefused(RuntimeError):
    """A different verdict file already holds this book-day (written once)."""


class NoJudge(JudgeStep):
    def __init__(self, root: Path):
        self.root = Path(root)

    def run(self, case: JudgeCase) -> Judged:
        blocks = case.book == BOOK2_HYBRID
        verdict = {
            "schema_version": 1, "kind": "judge_verdict", "book": case.book, "day": case.day.isoformat(),
            "judge": JUDGE_ID, "author_model": case.registered_model, "status": UNAVAILABLE, "blocks": blocks,
            "reason": NOT_BUILT, "checks": [], "suspended_by": None, "elapsed_ms": 0, "decision": dict(case.decision),
            "decision_sha256": sha256_hex(canonical_json(dict(case.decision))),
            "common_pack_sha256": case.common_sha256, "private_pack_sha256": case.private_sha256,
        }  # fmt: skip
        path = judge_path(case.day, case.book)
        write_once(self.root / path, json.dumps(verdict, sort_keys=True, indent=1, ensure_ascii=False) + "\n")
        return Judged(JudgeVerdict(UNAVAILABLE, blocks, NOT_BUILT), path)


def write_once(path: Path, text: str) -> None:
    """The same bytes again are accepted; different bytes are refused (a verdict is never rewritten)."""
    if path.is_file():
        if path.read_text(encoding="utf-8") != text:
            raise VerdictRefused(f"{path.name} already holds a different verdict (written once)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
