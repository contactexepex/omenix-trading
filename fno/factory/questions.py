"""The registered research questions (story R1c, FACTORY_RULES section 3 rule 3): `research/factory/questions.csv`,
append-only. Each shadow names one question; the question's Holm family is every shadow ever registered on it, and
its alpha is the family's one-sided level."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .append_only import AppendOnlyCsv, FileHistory
from .constants import QUESTION_COLUMNS, QUESTIONS_FILE
from .fields import CardError, Fields


class QuestionError(ValueError):
    """The question is refused, or the file's history is not append-only."""


@dataclass(frozen=True)
class Question:
    question_id: str
    question: str
    alpha: float


class Questions:
    def __init__(self, root: Path, history: FileHistory):
        self.store = AppendOnlyCsv(root, QUESTIONS_FILE, QUESTION_COLUMNS, history, QuestionError)

    def all(self) -> dict[str, Question]:
        self.store.require_append_only()
        rows = [Question(qid, text, float(alpha)) for qid, text, alpha in self.store.lines()]
        return {row.question_id: row for row in rows}

    def get(self, question_id: str) -> Question:
        found = self.all().get(question_id)
        if found is None:
            raise QuestionError(f"research question '{question_id}' is not in {QUESTIONS_FILE}: add it first")
        return found

    def add(self, question_id: str, question: str, alpha: float) -> Question:
        fields = Fields({"question_id": question_id, "question": question, "alpha": alpha}, QUESTIONS_FILE)
        try:
            row = Question(fields.slug("question_id"), fields.text("question"), fields.probability("alpha"))
        except CardError as bad:
            raise QuestionError(str(bad)) from bad
        if not 0 < row.alpha < 0.5:
            raise QuestionError(f"alpha {row.alpha} must be a one-sided level between 0 and 0.5")
        if row.question_id in self.all():
            raise QuestionError(f"research question '{row.question_id}' is already registered (never edited)")
        self.store.append((row.question_id, row.question, f"{row.alpha:g}"))
        return row
