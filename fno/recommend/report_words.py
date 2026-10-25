"""The recommender's words in the 08:50 and 20:05 editions (story REC1d, item 7), and their guard. Every line is one of
the templates here, REC1b's answer words (`post.py`) or REC1c's check words (`check_text.py`). A check's stored problem
is shown only when it reads as one of REC1c's own problem templates, whose fields are record paths, keys, versions,
counts and exception classes; any other text is withheld and its check file named instead (judge 664.1's note)."""

from __future__ import annotations

import re
from string import Formatter

from .check import MISMATCH
from .check_record import NEVER_CLOSED
from .outcomes import DESK_NOT_BUILT, NO_DECISION, ORPHAN, TWO_LIVE

TITLE = "Recommender, PAPER ONLY"
STANDING = "Standing; today's answer at about 15:20. From the recommendation of {day:%d %b %Y}:"
RUNG = "{version}: rung {rung} ({name})"
RUNGS = "Rungs: {rungs}."
NO_VERSIONS = "Rungs: no version rated."
NOTHING_YET = "No recommendation recorded yet."
NOT_READ = "The recommendation of {day:%d %b %Y} was not read ({path}, {kind})."
CHECK = "Check of {day:%d %b %Y} on {on:%d %b %Y}: {verdict}. {answer} {trades}"
CHECK_NOT_READ = "Check of {day:%d %b %Y} on {on:%d %b %Y} was not read ({path}, {kind})."
NOT_KNOWN = "{open} position(s) still open, so the day is not known yet."
# A check that ran and failed for a day writes no file (it alerts), so the line says only what is missing (K 666 m1)
NOT_DATED = "No check of {days} is dated the previous session ({on:%d %b %Y}); still waiting."
NO_CHECKS = "No check is due from the previous session ({on:%d %b %Y})."
TONIGHT = "Tonight's check runs after this edition; it is on #fno-desk and in tomorrow's 08:50."
NO_RECORD = "No recommendation recorded for {day:%d %b %Y}."
NO_RECORD_STEP = "No recommendation recorded for {day:%d %b %Y} (recommend step: {status}, {reason})."
WITHHELD = "a problem whose text is not shown here; see {path}"
SECTION_FAILED = "recommender {edition} section not made ({failure}); the edition was posted without it"

FIELD = {"count": r"\d+", "sessions": r"\d+", "kind": r"[A-Z]\w*"}
TOKEN = r"[\w./#@:-]+"  # a record path, a candidate key or a version: no spaces, so no free text
PATH_AND_CLASS = "{path}: {kind}"  # REC1c's read failures: `<data-area path>: <ExceptionClass>`
PROBLEMS = (NEVER_CLOSED, MISMATCH, NO_DECISION, ORPHAN, TWO_LIVE, DESK_NOT_BUILT, PATH_AND_CLASS)


def _pattern(template: str) -> re.Pattern:
    parts = [re.escape(text) + (f"(?:{FIELD.get(name, TOKEN)})" if name is not None else "")
             for text, name, _, _ in Formatter().parse(template)]  # fmt: skip
    return re.compile("".join(parts))


ALLOWED_PROBLEMS = tuple(_pattern(t) for t in PROBLEMS)


def shown_problem(problem: str, path: str) -> str:
    """The stored problem when it is one of REC1c's templates; otherwise withheld, naming the check file."""
    return problem if any(p.fullmatch(problem) for p in ALLOWED_PROBLEMS) else WITHHELD.format(path=path)
