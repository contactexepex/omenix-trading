"""The routine adapter of the advocate port (story LR1): a Claude routine writes `<subject>_objections.md` beside the
committed lines file. Its first line is the lines' SHA-256, then 1 to 5 objections, each one line `[L<n>] <sentence>`
naming the line it questions, at most 40 words, with no link, mention or code block, and with numbers only as whole
tokens of the lines (`numbers.py`). Any failed rule means the objections are not shown."""

from __future__ import annotations

import re
from pathlib import Path

from .numbers import form_failure, number_failure, number_tokens, sha_failure
from .port import Advocate, AdvocateResult, AdvocateSubject

SUFFIX = "_objections.md"
MAX_OBJECTIONS, MAX_WORDS = 5, 40
OBJECTION = re.compile(r"^\[L(\d+)\] (\S.*)$")
NO_FILE = "no objections received"
COUNT = "rule 2: {count} objections (1 to {most} allowed)"
SHAPE = "rule 2: objection {n} does not start with [L<line>] for a line of the lines file"


def objections_path(lines_path: Path) -> Path:
    return lines_path.with_name(lines_path.stem + SUFFIX)


class ObjectionCheck:
    def __init__(self, lines_text: str, lines_sha256: str):
        self.line_count, self.sha = len(lines_text.splitlines()), lines_sha256
        self.allowed = number_tokens(lines_text)

    def check(self, text: str) -> tuple[tuple[str, ...], str | None]:
        """(the objections, None) when every rule holds, else ((), the first failed rule)."""
        failure, rest = sha_failure(text, self.sha)
        found = [line.strip() for line in rest if line.strip()]
        if failure is None and not 1 <= len(found) <= MAX_OBJECTIONS:
            failure = COUNT.format(count=len(found), most=MAX_OBJECTIONS)
        for n, line in enumerate(found if failure is None else [], start=1):
            failure = self._objection_failure(n, line)
            if failure:
                break
        return ((), failure) if failure else (tuple(found), None)

    def _objection_failure(self, n: int, line: str) -> str | None:
        match = OBJECTION.match(line)
        if match is None or not 1 <= int(match.group(1)) <= self.line_count:
            return SHAPE.format(n=n)
        sentence = match.group(2)
        return form_failure(sentence, MAX_WORDS) or number_failure(sentence, self.allowed)


class RoutineFileAdvocate(Advocate):
    def objections(self, subject: AdvocateSubject) -> AdvocateResult:
        path = objections_path(subject.lines_path)
        if not path.is_file():
            return AdvocateResult(not_run=NO_FILE)
        lines_text = subject.lines_path.read_text(encoding="utf-8")
        found, failure = ObjectionCheck(lines_text, subject.lines_sha256).check(path.read_text(encoding="utf-8"))
        return AdvocateResult(not_run=failure) if failure else AdvocateResult(found)
